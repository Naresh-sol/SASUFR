"""
Attendance Window - Take Attendance using Face Recognition + Liveness Detection

Features:
1. Select Class, Subject, Start/End Time based on teacher's access
2. Start camera for 10 seconds
3. Detect and recognize multiple faces simultaneously
4. Liveness detection (MTCNN eye blink detection) to prevent spoofing
5. Mark attendance for recognized students in the database
6. Navigate to dashboard after completion
"""

import os
import sys
import cv2
import numpy as np
from datetime import datetime, date
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal

# Add the logic folder to import path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logic'))
from db_config import (
    get_teacher_classes_and_subjects,
    get_face_embeddings_by_class,
    create_attendance_session,
    mark_attendance
)
from face_recognition_logic import FaceRecognizer
from liveness_detection import LivenessDetector
from utils import create_font

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_resource_path(filename):
    return os.path.join(SCRIPT_DIR, filename)


# ══════════════════════════════════════════════
# CAMERA THREAD — runs face recognition in background
# ══════════════════════════════════════════════
class AttendanceCameraThread(QThread):
    """Thread for attendance camera capture, face recognition, and liveness detection."""
    frame_ready = pyqtSignal(np.ndarray)           # Each processed frame
    face_recognized = pyqtSignal(dict)              # Emit when a new student is recognized
    capture_complete = pyqtSignal(list)              # List of all recognized students
    error_occurred = pyqtSignal(str)

    def __init__(self, class_id, duration=10):
        super().__init__()
        self.class_id = class_id
        self.duration = duration
        self.running = False
        self.face_recognizer = None
        self.liveness_detector = None
        self.recognized_students = {}   # student_id -> student info
        self.stored_encodings = []
        self.consecutive_live = {}       # student_id -> consecutive live frame count

    def run(self):
        """Run attendance camera — detect, recognize, check liveness."""
        try:
            # Initialize models
            self.face_recognizer = FaceRecognizer()
            self.liveness_detector = LivenessDetector()

            # Load stored encodings for the class
            self.load_stored_encodings()

            if not self.stored_encodings:
                self.error_occurred.emit(
                    "No registered students found for this class.\n"
                    "Please register student faces first."
                )
                return

            # Open camera
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                self.error_occurred.emit("Could not open camera.")
                return

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            self.running = True
            start_time = datetime.now()
            frame_count = 0
            process_every_n = 2          # Only run recognition every Nth frame
            cached_draw_info = []        # Cache bounding box + label info
            liveness_result = {'is_live': False, 'reason': 'No face'}

            while self.running:
                ret, frame = cap.read()
                if not ret:
                    continue

                # Mirror the frame
                frame = cv2.flip(frame, 1)
                display_frame = frame.copy()
                frame_count += 1

                # ── Run heavy recognition only every Nth frame ──
                if frame_count % process_every_n == 0:
                    # Downscale for faster detection
                    small_frame = cv2.resize(frame, (320, 240))
                    scale_x = frame.shape[1] / 320
                    scale_y = frame.shape[0] / 240

                    boxes, probs, faces, landmarks = self.face_recognizer.detect_faces(small_frame)

                    cached_draw_info = []  # Reset cache

                    if boxes is not None and len(boxes) > 0 and faces is not None:
                        # Scale boxes back to original resolution
                        scaled_boxes = []
                        for box in boxes:
                            if box is not None:
                                scaled_boxes.append([
                                    box[0] * scale_x, box[1] * scale_y,
                                    box[2] * scale_x, box[3] * scale_y
                                ])

                        # Scale landmarks to original resolution
                        scaled_landmarks = []
                        if landmarks is not None:
                            for lm in landmarks:
                                if lm is not None:
                                    scaled_lm = []
                                    for pt in lm:
                                        scaled_lm.append([pt[0] * scale_x, pt[1] * scale_y])
                                    scaled_landmarks.append(scaled_lm)

                        liveness_result = self.liveness_detector.check_liveness(
                            frame, scaled_boxes, scaled_landmarks
                        )

                        encodings = self.face_recognizer.encode_faces(faces)
                        current_frame_students = set()

                        for i, (sbox, encoding) in enumerate(zip(scaled_boxes, encodings)):
                            x1, y1, x2, y2 = map(int, sbox)

                            match = self.face_recognizer.recognize_face(
                                encoding, self.stored_encodings
                            )

                            if match:
                                student_id = match['student_id']
                                name = match['student_name']
                                current_frame_students.add(student_id)

                                if liveness_result['is_live']:
                                    # Track consecutive live frames
                                    self.consecutive_live[student_id] = \
                                        self.consecutive_live.get(student_id, 0) + 1
                                    
                                    if self.consecutive_live[student_id] >= 3:
                                        if student_id not in self.recognized_students:
                                            self.recognized_students[student_id] = match
                                            self.face_recognized.emit(match)
                                        cached_draw_info.append((x1, y1, x2, y2, name, 'green'))
                                    else:
                                        cached_draw_info.append((x1, y1, x2, y2,
                                                                f"{name} (live {self.consecutive_live[student_id]}/3)", 'yellow'))
                                else:
                                    self.consecutive_live[student_id] = 0
                                    cached_draw_info.append((x1, y1, x2, y2,
                                                            f"{name} (verifying...)", 'yellow'))
                            else:
                                cached_draw_info.append((x1, y1, x2, y2, "Unknown", 'red'))
                                
                        # Reset consecutive live frames for anyone who stepped out
                        for sid in list(self.consecutive_live.keys()):
                            if sid not in current_frame_students:
                                self.consecutive_live[sid] = 0
                    else:
                        liveness_result = {'is_live': False, 'reason': 'No face'}
                        self.consecutive_live.clear()

                # ── Draw cached bounding boxes (every frame) ──
                color_map = {
                    'green': (0, 255, 0),
                    'yellow': (0, 255, 255),
                    'red': (0, 0, 255)
                }
                for (x1, y1, x2, y2, label, clr) in cached_draw_info:
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), color_map[clr], 2)
                    cv2.putText(display_frame, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_map[clr], 2)

                # ── Overlays ──
                elapsed = (datetime.now() - start_time).seconds
                remaining = max(0, self.duration - elapsed)

                cv2.putText(display_frame, f"Time: {remaining}s",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                            (255, 255, 0), 2)
                cv2.putText(display_frame, f"Detected: {len(self.recognized_students)}",
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (0, 255, 255), 2)

                # Liveness status
                liveness_text = self.liveness_detector.get_status_text()
                is_live = liveness_result.get('is_live', False)
                blinks = liveness_result.get('blinks', 0)
                color = (0, 255, 0) if is_live else (0, 165, 255)
                status = "LIVE" if is_live else "Checking..."
                cv2.putText(display_frame, f"Liveness: {status}",
                            (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                            color, 2)
                cv2.putText(display_frame, liveness_text,
                            (10, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            (200, 200, 200), 1)
                
                # Debug overlay — shows EAR and blink info
                debug_text = liveness_result.get('debug_text', '')
                if debug_text:
                    cv2.putText(display_frame, debug_text,
                                (10, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                                (180, 180, 180), 1)
                reason = liveness_result.get('reason', '')
                if reason:
                    cv2.putText(display_frame, reason,
                                (10, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                                (0, 200, 255), 1)

                self.frame_ready.emit(display_frame)

                if elapsed >= self.duration:
                    break

            cap.release()

            # Emit all recognized students
            self.capture_complete.emit(list(self.recognized_students.values()))

        except Exception as e:
            self.error_occurred.emit(str(e))

    def load_stored_encodings(self):
        """Load stored face encodings from database for the selected class."""
        encodings_data = get_face_embeddings_by_class(self.class_id)

        if encodings_data:
            for record in encodings_data:
                encoding = self.face_recognizer.bytes_to_encoding(record['embedding'])
                self.stored_encodings.append({
                    'student_id': record['student_id'],
                    'student_name': record['student_name'],
                    'encoding': encoding
                })

    def stop(self):
        """Stop camera."""
        self.running = False


# ══════════════════════════════════════════════
# ATTENDANCE WINDOW
# ══════════════════════════════════════════════
class AttendanceWindow(QtWidgets.QMainWindow):
    
    def __init__(self, teacher_id=None):
        super().__init__()
        self.teacher_id = teacher_id
        self.camera_thread = None
        self.recognized_students = []
        self.session_id = None
        self.setup_ui()
        self.connect_signals()
        if self.teacher_id:
            self.load_teacher_data()
    
    def setup_ui(self):
        """Initialize and configure all UI elements."""
        # Window configuration
        self.setObjectName("AttendanceWindow")
        self.resize(709, 781)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowMaximizeButtonHint)
        self.setWindowTitle("Take Attendance")
        
        # Window icon
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(get_resource_path("Logo1.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(icon)
        
        # Central widget
        self.central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        # Main card frame
        self.card_frame = QtWidgets.QFrame(self.central_widget)
        self.card_frame.setGeometry(QtCore.QRect(140, 10, 461, 711))
        self.card_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                border: 1px solid #e0e0e0;
            }
        """)
        self.card_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.card_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        
        # Main title
        self.title_label = QtWidgets.QLabel(self.card_frame)
        self.title_label.setGeometry(QtCore.QRect(80, 10, 301, 61))
        self.title_label.setFont(create_font("Segoe UI", 22, bold=True))
        self.title_label.setStyleSheet("border: none;")
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        self.title_label.setText("Take Attendance")
        
        # Selection fields
        self._create_class_selector()
        self._create_subject_selector()
        self._create_start_time_selector()
        self._create_end_time_selector()
        
        # Take Attendance button
        self._create_attendance_button()
        
        # Status label (below button, above camera)
        self.status_label = QtWidgets.QLabel(self.card_frame)
        self.status_label.setGeometry(QtCore.QRect(60, 380, 341, 20))
        self.status_label.setFont(create_font("Segoe UI", 9))
        self.status_label.setStyleSheet("border: none; color: #6C757D;")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setText("")
        
        # Camera frame
        self._create_camera_frame()
        
        # Back button
        self._create_back_button()
        
        # Menu and status bars
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 709, 26))
        self.setMenuBar(self.menubar)
        
        self.statusbar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.statusbar)
    


    
    def _create_combo_field(self, label_text, y, items, enabled=True):
        """Create a label + combo box pair at given y position."""
        label = QtWidgets.QLabel(self.card_frame)
        label.setGeometry(QtCore.QRect(30, y, 101, 31))
        label.setFont(create_font("Segoe UI", 12))
        label.setStyleSheet("border: none;")
        label.setText(label_text)
        
        combo = QtWidgets.QComboBox(self.card_frame)
        combo.setGeometry(QtCore.QRect(130, y, 291, 41))
        combo.setFont(create_font("Segoe UI", 10))
        combo.setStyleSheet("""
            QComboBox { border-radius: 8px; border: 1px solid; padding: 10px; }
            QComboBox::drop-down { width: 0px; }
        """)
        combo.addItems(items)
        combo.setEnabled(enabled)
        return combo
    
    def _create_class_selector(self):
        """Create class selection combo box with label."""
        self.combo_class = self._create_combo_field("Class:", 100, ["---Select Class---"])
    
    def _create_subject_selector(self):
        """Create subject selection combo box with label."""
        self.combo_subject = self._create_combo_field("Subject:", 150, ["---Select Subject---"])
    
    def _create_start_time_selector(self):
        """Create start time selection combo box with label."""
        self.combo_start_time = self._create_combo_field("Start Time:", 200, [
            "---Select Start Time---",
            "8:00", "8:55", "9:50", "10:45",
            "11:40", "12:35", "1:30", "2:25", "3:20"
        ])
    
    def _create_end_time_selector(self):
        """Create end time selection combo box with label."""
        self.combo_end_time = self._create_combo_field("End Time:", 250, [
            "---Select End Time---",
            "8:55", "9:50", "10:45",
            "11:40", "12:35", "1:30", "2:25",
            "3:20", "4:15"
        ], enabled=False)
    
    def _create_attendance_button(self):
        """Create the Take Attendance button."""
        self.btn_take_attendance = QtWidgets.QPushButton(self.card_frame)
        self.btn_take_attendance.setGeometry(QtCore.QRect(60, 320, 341, 51))
        self.btn_take_attendance.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_take_attendance.setText("Take Attendance")
        self.btn_take_attendance.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #2adc4d, stop:1 #16a34a);
                color: white;
                border-radius: 8px;
                border: none;
                font-weight: bold;
                font-family: Arial;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #42e660, stop:1 #1eb854);
            }
            QPushButton:pressed {
                background-color: #16a34a;
            }
            QPushButton:disabled {
                background-color: #B0BEC5;
            }
        """)
    
    def _create_camera_frame(self):
        """Create the camera display frame."""
        self.camera_frame = QtWidgets.QFrame(self.card_frame)
        self.camera_frame.setGeometry(QtCore.QRect(60, 400, 341, 221))
        self.camera_frame.setStyleSheet("""
            background-color: #FFFFFF;
            border: 2px dashed #DEE2E6;
            border-radius: 12px;
        """)
        self.camera_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.camera_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        
        self.camera_display = QtWidgets.QLabel(self.camera_frame)
        self.camera_display.setGeometry(QtCore.QRect(40, 10, 261, 201))
        self.camera_display.setStyleSheet("border: none;")
        self.camera_display.setPixmap(QtGui.QPixmap(get_resource_path("Cam.png")))
        self.camera_display.setScaledContents(True)
        self.camera_display.setAlignment(QtCore.Qt.AlignCenter)
    
    def _create_back_button(self):
        """Create the Back to Login button with icon."""
        self.btn_back = QtWidgets.QPushButton("Back To Login", self.card_frame)
        self.btn_back.setGeometry(QtCore.QRect(60, 640, 160, 51))
        self.btn_back.setFont(create_font("Segoe UI", 10, bold=True))
        self.btn_back.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 2px solid #e0e0e0;
                border-radius: 16px;
                color: #555;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
            }
        """)
        
        self.btn_dashboard = QtWidgets.QPushButton("View Dashboard", self.card_frame)
        self.btn_dashboard.setGeometry(QtCore.QRect(240, 640, 160, 51))
        self.btn_dashboard.setFont(create_font("Segoe UI", 10, bold=True))
        self.btn_dashboard.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_dashboard.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #60a5fa, stop:1 #3b82f6);
                color: white;
                border-radius: 16px;
                border: none;
            }
            QPushButton:hover {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #93c5fd, stop:1 #60a5fa);
            }
        """)
    
    # ══════════════════════════════════════════════
    # SIGNAL CONNECTIONS
    # ══════════════════════════════════════════════
    def connect_signals(self):
        """Connect button signals to handler methods."""
        self.btn_take_attendance.clicked.connect(self.start_attendance)
        self.btn_back.clicked.connect(self.go_back_login)
        self.btn_dashboard.clicked.connect(self.open_dashboard)
        self.combo_start_time.currentIndexChanged.connect(self.on_start_time_changed)
    
    def on_start_time_changed(self):
        """Auto-select end time based on the selected start time."""
        # Start[1]="8:00" → End[1]="8:55", Start[9]="3:20" → End[9]="4:15"
        index = self.combo_start_time.currentIndex()
        self.combo_end_time.setCurrentIndex(index if index > 0 else 0)
    
    # ══════════════════════════════════════════════
    # DATA LOADING
    # ══════════════════════════════════════════════
    def load_teacher_data(self):
        """Fetch and populate class/subject dropdowns for the logged-in teacher."""
        data = get_teacher_classes_and_subjects(self.teacher_id)
        
        if data is None:
            QtWidgets.QMessageBox.warning(
                self, "Error", "Could not fetch your class/subject data."
            )
            return
        
        for cls in data['classes']:
            self.combo_class.addItem(cls['display_name'], cls['class_id'])
        
        for sub in data['subjects']:
            self.combo_subject.addItem(sub['subject_name'], sub['subject_id'])
    
    # ══════════════════════════════════════════════
    # ATTENDANCE LOGIC
    # ══════════════════════════════════════════════
    def get_selected_class(self):
        """Get selected class_id from combo box."""
        return self.combo_class.currentData()

    def get_selected_subject(self):
        """Get selected subject_id from combo box."""
        return self.combo_subject.currentData()

    def get_selected_start_time(self):
        """Get selected start time text."""
        text = self.combo_start_time.currentText()
        if text.startswith("---"):
            return None
        return text

    def get_selected_end_time(self):
        """Get selected end time text."""
        text = self.combo_end_time.currentText()
        if text.startswith("---"):
            return None
        return text

    def start_attendance(self):
        """Start the face recognition attendance process."""
        # ── Validate selections ──
        class_id = self.get_selected_class()
        subject_id = self.get_selected_subject()
        start_time = self.get_selected_start_time()
        end_time = self.get_selected_end_time()

        if class_id is None:
            QtWidgets.QMessageBox.warning(self, "Validation Error", "Please select a class.")
            return
        if subject_id is None:
            QtWidgets.QMessageBox.warning(self, "Validation Error", "Please select a subject.")
            return
        if start_time is None:
            QtWidgets.QMessageBox.warning(self, "Validation Error", "Please select a start time.")
            return
        if end_time is None:
            QtWidgets.QMessageBox.warning(self, "Validation Error", "Please select an end time.")
            return

        # ── Create attendance session in DB ──
        teacher_id = self.teacher_id or 'T01'
        current_date = date.today().strftime('%Y-%m-%d')

        self.session_id = create_attendance_session(
            teacher_id, subject_id, class_id,
            current_date, start_time, end_time
        )

        if not self.session_id:
            QtWidgets.QMessageBox.critical(
                self, "Error", "Failed to create attendance session in database."
            )
            return

        # ── Start camera thread ──
        self.btn_take_attendance.setEnabled(False)
        self.btn_take_attendance.setText("Taking Attendance...")
        self.status_label.setText("Scanning faces — please look at the camera...")

        self.camera_thread = AttendanceCameraThread(
            class_id=class_id,
            duration=10
        )
        self.camera_thread.frame_ready.connect(self.update_camera_frame)
        self.camera_thread.face_recognized.connect(self.on_face_recognized)
        self.camera_thread.capture_complete.connect(self.on_capture_complete)
        self.camera_thread.error_occurred.connect(self.on_capture_error)
        self.camera_thread.start()

    def update_camera_frame(self, frame):
        """Update the camera display with a new frame from the thread."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w

        q_image = QtGui.QImage(rgb_frame.data, w, h, bytes_per_line,
                               QtGui.QImage.Format_RGB888)
        pixmap = QtGui.QPixmap.fromImage(q_image)
        scaled = pixmap.scaled(261, 201,
                               QtCore.Qt.KeepAspectRatio,
                               QtCore.Qt.SmoothTransformation)
        self.camera_display.setPixmap(scaled)

    def on_face_recognized(self, match):
        """Handle a newly recognized face."""
        self.status_label.setText(f"Recognized: {match['student_name']}")

    def on_capture_complete(self, recognized_students):
        """Handle capture completion — mark attendance in DB."""
        self.recognized_students = recognized_students
        self.btn_take_attendance.setEnabled(True)
        self.btn_take_attendance.setText("Take Attendance")

        # Mark attendance for each recognized student
        present_count = 0
        for student in recognized_students:
            success = mark_attendance(
                self.session_id,
                student['student_id'],
                'Present'
            )
            if success:
                present_count += 1

        # Reset camera preview
        self.camera_display.setPixmap(
            QtGui.QPixmap(get_resource_path("Cam.png"))
        )

        self.status_label.setText(
            f"Attendance marked for {present_count} student(s)"
        )

        # Ask to view dashboard
        reply = QtWidgets.QMessageBox.question(
            self, "Attendance Complete",
            f"Marked {present_count} student(s) as present.\n\n"
            f"Would you like to view the dashboard?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            self.open_dashboard()

    def on_capture_error(self, error_msg):
        """Handle capture error."""
        self.btn_take_attendance.setEnabled(True)
        self.btn_take_attendance.setText("Take Attendance")
        self.status_label.setText("")
        QtWidgets.QMessageBox.critical(self, "Error", f"Error: {error_msg}")

    # ══════════════════════════════════════════════
    # NAVIGATION
    # ══════════════════════════════════════════════
    def go_back_login(self):
        """Navigate back to the Login window."""
        from Login_window import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()
    
    def open_dashboard(self):
        """Navigate to the Dashboard window."""
        from Dashboard_window import DashboardWindow
        class_id = self.get_selected_class()
        subject_id = self.get_selected_subject()
        
        self.dashboard_window = DashboardWindow(
            teacher_id=self.teacher_id,
            pre_select_class=class_id,
            pre_select_subject=subject_id
        )
        self.dashboard_window.show()
        self.close()

    def closeEvent(self, event):
        """Stop camera thread when window is closed."""
        if self.camera_thread and self.camera_thread.isRunning():
            self.camera_thread.stop()
            self.camera_thread.wait()
        event.accept()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = AttendanceWindow()
    window.show()
    sys.exit(app.exec_())
