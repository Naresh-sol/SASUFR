

import os
import sys
from PyQt5 import QtCore, QtGui, QtWidgets

# Add the logic folder to the path so we can import from it
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logic'))
from face_register_logic import FaceRegisterLogic
from utils import create_font

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_resource_path(filename):
    """Get the absolute path to a resource file in the script's directory."""
    return os.path.join(SCRIPT_DIR, filename)


class RegisterFaceWindow(QtWidgets.QMainWindow):
    """Window for registering student faces."""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.connect_signals()
        
        # ── Initialize logic handler ──
        self.logic = FaceRegisterLogic()
        self.verified_student_id = None
        
        # Camera preview timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_camera_preview)
    
    def setup_ui(self):
        """Initialize and configure all UI elements."""
        # Window configuration
        self.setObjectName("RegisterFaceWindow")
        self.resize(800, 790)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowMaximizeButtonHint)
        self.setWindowTitle("Face Registration")
        
        # Window icon
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(get_resource_path("Logo1.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(icon)
        
        # Central widget
        self.central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        # Main card frame
        self.card_frame = QtWidgets.QFrame(self.central_widget)
        self.card_frame.setGeometry(QtCore.QRect(190, 30, 441, 691))
        self.card_frame.setStyleSheet(
            "background-color: white; border-radius: 16px; border: none;"
        )
        self.card_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        
        # Title
        self.title_label = QtWidgets.QLabel(self.card_frame)
        self.title_label.setGeometry(QtCore.QRect(50, 0, 341, 81))
        self.title_label.setFont(create_font("Segoe UI", 22, bold=True))
        self.title_label.setStyleSheet("border: none;")
        self.title_label.setText("Face Registration")
        
        # Subtitle
        self.subtitle_label = QtWidgets.QLabel(self.card_frame)
        self.subtitle_label.setGeometry(QtCore.QRect(60, 80, 321, 31))
        self.subtitle_label.setFont(create_font("Segoe UI", 10))
        self.subtitle_label.setStyleSheet("border: none;")
        self.subtitle_label.setText("Register your face for smart attendance")
        
        # Student ID section
        self._create_student_id_section()
        
        # Camera preview section
        self._create_camera_section()
        
        # Back button
        self.btn_back = QtWidgets.QPushButton(self.card_frame)
        self.btn_back.setGeometry(QtCore.QRect(80, 610, 281, 51))
        self.btn_back.setFont(create_font("Segoe UI", 10))
        self.btn_back.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_back.setText("Back To Home")
        self.btn_back.setStyleSheet("border-radius: 16px; border: 1px solid #e0e0e0;")
        
        # Back arrow icon
        self.back_arrow = QtWidgets.QLabel(self.card_frame)
        self.back_arrow.setGeometry(QtCore.QRect(110, 620, 41, 31))
        self.back_arrow.setStyleSheet("border: none;")
        self.back_arrow.setPixmap(QtGui.QPixmap(get_resource_path("back arrow.jpg")))
        self.back_arrow.setScaledContents(True)
        
        # Menu and status bars
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 26))
        self.setMenuBar(self.menubar)
        
        self.statusbar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.statusbar)

    
    def _create_student_id_section(self):
        """Create student ID input, password input, and verify button."""
        # Student ID label
        self.student_id_label = QtWidgets.QLabel(self.card_frame)
        self.student_id_label.setGeometry(QtCore.QRect(40, 140, 111, 41))
        self.student_id_label.setFont(create_font("Segoe UI", 12))
        self.student_id_label.setStyleSheet("border: none;")
        self.student_id_label.setText("Student ID:")
        
        # Student ID input
        self.input_student_id = QtWidgets.QLineEdit(self.card_frame)
        self.input_student_id.setGeometry(QtCore.QRect(150, 140, 241, 41))
        self.input_student_id.setFont(create_font("Segoe UI", 10))
        self.input_student_id.setStyleSheet(
            "border: 1px solid; border-radius: 16px; padding: 10px;"
        )
        self.input_student_id.setPlaceholderText("Enter your Student ID")
        
        # Password label
        self.password_label = QtWidgets.QLabel(self.card_frame)
        self.password_label.setGeometry(QtCore.QRect(40, 195, 111, 41))
        self.password_label.setFont(create_font("Segoe UI", 12))
        self.password_label.setStyleSheet("border: none;")
        self.password_label.setText("Password:")
        
        # Password input
        self.input_password = QtWidgets.QLineEdit(self.card_frame)
        self.input_password.setGeometry(QtCore.QRect(150, 195, 241, 41))
        self.input_password.setFont(create_font("Segoe UI", 10))
        self.input_password.setStyleSheet(
            "border: 1px solid; border-radius: 16px; padding: 10px;"
        )
        self.input_password.setPlaceholderText("Enter your Password")
        self.input_password.setEchoMode(QtWidgets.QLineEdit.Password)
        
        # Verify button
        self.btn_verify = QtWidgets.QPushButton(self.card_frame)
        self.btn_verify.setGeometry(QtCore.QRect(90, 260, 251, 41))
        self.btn_verify.setFont(create_font("Segoe UI", 12, bold=True))
        self.btn_verify.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_verify.setText("Verify Student")
        self.btn_verify.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
    
    def _create_camera_section(self):
        """Create camera preview and capture button."""
        # Camera frame
        self.camera_frame = QtWidgets.QFrame(self.card_frame)
        self.camera_frame.setGeometry(QtCore.QRect(60, 320, 321, 261))
        self.camera_frame.setStyleSheet(
            "background-color: #FFFFFF; border: 2px dashed #DEE2E6; border-radius: 12px;"
        )
        self.camera_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        
        # Camera preview label
        self.camera_preview = QtWidgets.QLabel(self.camera_frame)
        self.camera_preview.setGeometry(QtCore.QRect(40, 5, 251, 181))
        self.camera_preview.setStyleSheet("border: none;")
        self.camera_preview.setPixmap(QtGui.QPixmap(get_resource_path("face_register1.png")))
        self.camera_preview.setScaledContents(True)
        
        # Capture button
        self.btn_capture = QtWidgets.QPushButton(self.camera_frame)
        self.btn_capture.setGeometry(QtCore.QRect(40, 200, 251, 41))
        self.btn_capture.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_capture.setText("Capture & Register Face")
        self.btn_capture.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #3b82f6, stop:1 #2563eb);
                color: white;
                border-radius: 8px;
                border: none;
                font-weight: bold;
                font-family: Arial;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #60a5fa, stop:1 #3b82f6);
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
    
    # ══════════════════════════════════════════════
    # SIGNAL CONNECTIONS (buttons → actions)
    # ══════════════════════════════════════════════
    def connect_signals(self):
        """Connect button signals to methods."""
        self.btn_back.clicked.connect(self.go_back_home)
        self.btn_verify.clicked.connect(self.verify_student)
        self.btn_capture.clicked.connect(self.capture_face)
    
    # ══════════════════════════════════════════════
    # GUI ACTIONS (call logic, show results)
    # ══════════════════════════════════════════════
    def verify_student(self):
        """Verify student ID and password — delegates to logic, shows result in GUI."""
        student_id = self.input_student_id.text().strip()
        password = self.input_password.text().strip()
        
        if not student_id or not password:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Please enter both Student ID and Password."
            )
            return
        
        # Delegate to logic layer — now uses password authentication
        student_info = self.logic.authenticate_student(student_id, password)
        
        if student_info:
            self.verified_student_id = student_id
            QtWidgets.QMessageBox.information(
                self,
                "Student Verified",
                f"Student found: {student_info['student_name']}\n\n"
                f"Please look at the camera and click 'Capture & Register Face'."
            )
            # Start camera preview
            if self.logic.start_camera():
                self.timer.start(30)  # ~33 FPS
            else:
                QtWidgets.QMessageBox.critical(
                    self, "Camera Error", "Could not access the webcam."
                )
        else:
            self.verified_student_id = None
            QtWidgets.QMessageBox.critical(
                self,
                "Authentication Failed",
                f"Invalid Student ID or Password.\n"
                f"Please check your credentials and try again."
            )
    
    def update_camera_preview(self):
        """Read a frame from logic and display it in the GUI."""
        ret, frame = self.logic.read_frame()
        if ret:
            import cv2

            # Detect faces and draw blue bounding boxes
            boxes = self.logic.detect_faces(frame)
            for (x1, y1, x2, y2) in boxes:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)  # Blue in BGR

            # Convert BGR (OpenCV) → RGB (Qt)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qt_image = QtGui.QImage(
                frame_rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888
            )
            pixmap = QtGui.QPixmap.fromImage(qt_image)
            self.camera_preview.setPixmap(pixmap)
            self.camera_preview.setScaledContents(True)
    
    def capture_face(self):
        """Capture face — delegates to logic, shows result in GUI."""
        if self.verified_student_id is None:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Please verify a Student ID first."
            )
            return
        
        # Read current frame
        ret, frame = self.logic.read_frame()
        if not ret:
            QtWidgets.QMessageBox.critical(
                self, "Error", "Camera is not active or failed to capture."
            )
            return
        
        # Delegate face detection + embedding + DB save to logic
        success, message = self.logic.register_face(self.verified_student_id, frame)
        
        if success:
            QtWidgets.QMessageBox.information(self, "Success", message)
            self.stop_camera()
            self.verified_student_id = None
            self.input_student_id.clear()
            self.input_password.clear()
        else:
            QtWidgets.QMessageBox.warning(self, "Failed", message)
    
    def stop_camera(self):
        """Stop the camera preview and release resources."""
        self.timer.stop()
        self.logic.stop_camera()
        self.camera_preview.setPixmap(
            QtGui.QPixmap(get_resource_path("face_register1.png"))
        )
    
    # ══════════════════════════════════════════════
    # NAVIGATION
    # ══════════════════════════════════════════════
    def go_back_home(self):
        """Navigate back to Home window."""
        self.stop_camera()
        from Home_window import HomeWindow
        self.home_window = HomeWindow()
        self.home_window.show()
        self.close()
    
    def closeEvent(self, event):
        """Release camera when window is closed."""
        self.stop_camera()
        event.accept()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = RegisterFaceWindow()
    window.show()
    sys.exit(app.exec_())
