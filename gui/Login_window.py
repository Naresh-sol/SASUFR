"""
Login Window - Teacher Login for Smart Attendance System
Navigation:
  - "Login" button -> Attendance Window (after authentication)
  - "Back To Home" button -> Home Window
"""
import os
import sys
from PyQt5 import QtCore, QtGui, QtWidgets

# Add the logic folder to import path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logic'))
from db_config import authenticate_teacher
from utils import create_font

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_resource_path(filename):
    """Get the absolute path to a resource file in the script's directory."""
    return os.path.join(SCRIPT_DIR, filename)


class LoginWindow(QtWidgets.QMainWindow):
    """Login window for teacher authentication."""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Initialize and configure all UI elements."""
        # Window configuration
        self.setObjectName("LoginWindow")
        self.resize(635, 600)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowMaximizeButtonHint)
        self.setWindowTitle("Teacher Login")
        
        # Window icon
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(get_resource_path("Logo1.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(icon)
        
        # Central widget
        self.central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        # Main card frame
        self.card_frame = QtWidgets.QFrame(self.central_widget)
        self.card_frame.setGeometry(QtCore.QRect(70, 30, 501, 501))
        self.card_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                border: 1px solid #e0e0e0;
            }
        """)
        self.card_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        
        # Title
        self.title_label = QtWidgets.QLabel(self.card_frame)
        self.title_label.setGeometry(QtCore.QRect(40, 10, 411, 81))
        self.title_label.setFont(create_font("Segoe UI", 20, bold=True))
        self.title_label.setStyleSheet("border: none;")
        self.title_label.setText("Smart Attendance System")
        
        # Subtitle
        self.subtitle_label = QtWidgets.QLabel(self.card_frame)
        self.subtitle_label.setGeometry(QtCore.QRect(180, 80, 121, 41))
        self.subtitle_label.setFont(create_font("Segoe UI", 12))
        self.subtitle_label.setStyleSheet("border: none;")
        self.subtitle_label.setText("Teacher Login")
        
        # Username field
        self._create_username_field()
        
        # Password field
        self._create_password_field()
        
        # Login button
        self.btn_login = QtWidgets.QPushButton(self.card_frame)
        self.btn_login.setGeometry(QtCore.QRect(20, 310, 341, 51))
        self.btn_login.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_login.setText("Login")
        self.btn_login.setStyleSheet("""
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
        """)
        
        # Back button
        self.btn_back = QtWidgets.QPushButton(self.card_frame)
        self.btn_back.setGeometry(QtCore.QRect(20, 380, 281, 51))
        self.btn_back.setFont(create_font("Segoe UI", 10))
        self.btn_back.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_back.setText("Back To Home")
        self.btn_back.setStyleSheet("border-radius: 16px; border: 1px solid #e0e0e0;")
        
        # Back arrow icon
        self.back_arrow = QtWidgets.QLabel(self.card_frame)
        self.back_arrow.setGeometry(QtCore.QRect(50, 390, 41, 31))
        self.back_arrow.setStyleSheet("border: none;")
        self.back_arrow.setPixmap(QtGui.QPixmap(get_resource_path("back arrow.jpg")))
        self.back_arrow.setScaledContents(True)
        
        # Teacher illustration
        self.teacher_image = QtWidgets.QLabel(self.card_frame)
        self.teacher_image.setGeometry(QtCore.QRect(320, 360, 171, 121))
        self.teacher_image.setStyleSheet("border: none;")
        self.teacher_image.setPixmap(QtGui.QPixmap(get_resource_path("teacher_login.png")))
        self.teacher_image.setScaledContents(True)
        
        # Menu and status bars
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 635, 26))
        self.setMenuBar(self.menubar)
        
        self.statusbar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.statusbar)

    
    def _create_username_field(self):
        """Create username input field with icon."""
        # Username input (create first so it's behind)
        self.input_username = QtWidgets.QLineEdit(self.card_frame)
        self.input_username.setGeometry(QtCore.QRect(20, 150, 371, 51))
        self.input_username.setFont(create_font("Segoe UI", 10))
        self.input_username.setStyleSheet(
            "border-radius: 16px; border: 1px solid; padding: 50px;"
        )
        self.input_username.setPlaceholderText("Username")
        
        # User icon (create after input so it's on top)
        self.user_icon = QtWidgets.QLabel(self.card_frame)
        self.user_icon.setGeometry(QtCore.QRect(30, 160, 38, 38))
        self.user_icon.setStyleSheet("border-radius: 16px; border: none;")
        self.user_icon.setPixmap(QtGui.QPixmap(get_resource_path("user.jpg")))
        self.user_icon.setScaledContents(True)
        self.user_icon.raise_()  # Ensure icon is above input
    
    def _create_password_field(self):
        """Create password input field with icon."""
        # Password input (create first so it's behind)
        self.input_password = QtWidgets.QLineEdit(self.card_frame)
        self.input_password.setGeometry(QtCore.QRect(20, 220, 371, 51))
        self.input_password.setFont(create_font("Segoe UI", 10))
        self.input_password.setStyleSheet(
            "border-radius: 16px; border: 1px solid; padding: 50px;"
        )
        self.input_password.setPlaceholderText("Password")
        self.input_password.setEchoMode(QtWidgets.QLineEdit.Password)
        
        # Lock icon (create after input so it's on top)
        self.lock_icon = QtWidgets.QLabel(self.card_frame)
        self.lock_icon.setGeometry(QtCore.QRect(30, 230, 38, 38))
        self.lock_icon.setStyleSheet("border: none;")
        self.lock_icon.setPixmap(QtGui.QPixmap(get_resource_path("lock.png")))
        self.lock_icon.setScaledContents(True)
        self.lock_icon.raise_()  # Ensure icon is above input
    
    def open_attendance(self):
        """Navigate to Attendance window after login."""
        from Attendance_window import AttendanceWindow
        self.attendance_window = AttendanceWindow(self.teacher_id)
        self.attendance_window.show()
        self.close()
    
    def go_back_home(self):
        """Navigate back to Home window."""
        from Home_window import HomeWindow
        self.home_window = HomeWindow()
        self.home_window.show()
        self.close()

    def connect_signals(self):
        """Connect button signals to navigation methods."""
        self.btn_login.clicked.connect(self.authenticate)  # ← changed from open_attendance
        self.btn_back.clicked.connect(self.go_back_home)

    # ─── ADD this new method to LoginWindow class ───
    def authenticate(self):
        """
        Authenticate teacher credentials against the database.
        
        STEP-BY-STEP:
            1. Read what the teacher typed in the username and password fields.
            2. Check if either field is empty → show warning.
            3. Call authenticate_teacher() from db_config.py.
            4. If it returns a dict → login successful → open Attendance window.
            5. If it returns None → login failed → show error message.
        """
        # Step 1: Get text from input fields
        username = self.input_username.text().strip()
        password = self.input_password.text().strip()
        # .strip() removes accidental leading/trailing spaces
        
        # Step 2: Validate — don't even query DB if fields are empty
        if not username or not password:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Please enter both username and password."
            )
            return
        
        # Step 3: Query the database
        teacher_info = authenticate_teacher(username, password)
        
        # Step 4 & 5: Check result
        if teacher_info:
            # Login successful!
            QtWidgets.QMessageBox.information(
                self, 
                "Success", 
                f"Welcome, {teacher_info['teacher_name']}!"
            )
            self.teacher_id = teacher_info['teacher_id']
            self.open_attendance()
        else:
            # Login failed
            QtWidgets.QMessageBox.critical(
                self, 
                "Login Failed", 
                "Invalid username or password. Please try again."
            )
            self.input_username.clear()  # Clear username field for retry
            self.input_password.clear()  # Clear password field for retry

        
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())
