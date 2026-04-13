"""
Home Window - Main entry point for Smart Attendance System
Navigation:
  - "Take Attendance" button -> Login Window
  - "Register Face" button -> Register Face Window
"""

import os
import warnings

# Suppress PyQt5-related SIP deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, message="sipPyTypeDict")

from PyQt5 import QtCore, QtGui, QtWidgets
from utils import create_font

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_resource_path(filename):
    """Get the absolute path to a resource file in the script's directory."""
    return os.path.join(SCRIPT_DIR, filename)


class HomeWindow(QtWidgets.QMainWindow):
    """Main home window with two options: Register Face and Take Attendance."""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Initialize and configure all UI elements."""
        # Window configuration
        self.setObjectName("HomeWindow")
        self.resize(1049, 691)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowMaximizeButtonHint)
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.setWindowTitle("Smart Attendance System")
        
        # Window icon
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(get_resource_path("Logo1.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(icon)
        
        # Central widget
        self.central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.central_widget) 
        
        # Main title
        self.title_label = QtWidgets.QLabel(self.central_widget)
        self.title_label.setGeometry(QtCore.QRect(0, 40, 1050, 50))
        self.title_label.setFont(create_font("Arial", 28, bold=True))
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        self.title_label.setText("Smart Attendance System")
        
        # Subtitle
        self.subtitle_label = QtWidgets.QLabel(self.central_widget)
        self.subtitle_label.setGeometry(QtCore.QRect(220, 110, 600, 60))
        self.subtitle_label.setFont(create_font("Arial", 11))
        self.subtitle_label.setAlignment(QtCore.Qt.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setText(
            "A smart attendance management system based on face recognition "
            "to automatically mark attendance for students"
        )
        
        # Create cards
        self._create_register_card()
        self._create_attendance_card()
        
        # Menu and status bars
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1049, 26))
        self.setMenuBar(self.menubar)
        
        self.statusbar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.statusbar)

    
    def _create_register_card(self):
        """Create the Register Face card."""
        # Card frame
        self.card_register = QtWidgets.QFrame(self.central_widget)
        self.card_register.setGeometry(QtCore.QRect(90, 210, 420, 400))
        self.card_register.setStyleSheet(
            "background-color: white; border-radius: 16px; border: 1px solid #e0e0e0;"
        )
        self.card_register.setFrameShape(QtWidgets.QFrame.StyledPanel)
        
        # Card title
        self.register_title = QtWidgets.QLabel(self.card_register)
        self.register_title.setGeometry(QtCore.QRect(10, 20, 400, 35))
        self.register_title.setFont(create_font("Arial", 18, bold=True))
        self.register_title.setStyleSheet("border: none;")
        self.register_title.setAlignment(QtCore.Qt.AlignCenter)
        self.register_title.setText("Register Face")
        
        # Card image
        self.register_image = QtWidgets.QLabel(self.card_register)
        self.register_image.setGeometry(QtCore.QRect(70, 60, 281, 211))
        self.register_image.setStyleSheet("border: none;")
        self.register_image.setPixmap(QtGui.QPixmap(get_resource_path("stud_reg.png")))
        self.register_image.setScaledContents(True)
        self.register_image.setAlignment(QtCore.Qt.AlignCenter)
        
        # Card description
        self.register_desc = QtWidgets.QLabel(self.card_register)
        self.register_desc.setGeometry(QtCore.QRect(20, 270, 380, 50))
        self.register_desc.setFont(create_font("Arial", 10))
        self.register_desc.setStyleSheet("color: #666666; border: none;")
        self.register_desc.setAlignment(QtCore.Qt.AlignCenter)
        self.register_desc.setWordWrap(True)
        self.register_desc.setText(
            "Register faces of students by capturing their photo and details"
        )
        
        # Register button
        self.btn_register = QtWidgets.QPushButton(self.card_register)
        self.btn_register.setGeometry(QtCore.QRect(100, 330, 200, 45))
        self.btn_register.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_register.setText("Register Face")
        self.btn_register.setStyleSheet("""
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
        
        # Raise elements above image
        self.register_image.raise_()
        self.register_title.raise_()
        self.register_desc.raise_()
        self.btn_register.raise_()
    
    def _create_attendance_card(self):
        """Create the Take Attendance card."""
        # Card frame
        self.card_attendance = QtWidgets.QFrame(self.central_widget)
        self.card_attendance.setGeometry(QtCore.QRect(560, 210, 420, 400))
        self.card_attendance.setStyleSheet(
            "background-color: white; border-radius: 16px; border: 1px solid #e0e0e0;"
        )
        self.card_attendance.setFrameShape(QtWidgets.QFrame.StyledPanel)
        
        # Card title
        self.attendance_title = QtWidgets.QLabel(self.card_attendance)
        self.attendance_title.setGeometry(QtCore.QRect(10, 20, 400, 35))
        self.attendance_title.setFont(create_font("Arial", 18, bold=True))
        self.attendance_title.setStyleSheet("border: none;")
        self.attendance_title.setAlignment(QtCore.Qt.AlignCenter)
        self.attendance_title.setText("Take Attendance")
        
        # Card image
        self.attendance_image = QtWidgets.QLabel(self.card_attendance)
        self.attendance_image.setGeometry(QtCore.QRect(40, 40, 341, 221))
        self.attendance_image.setStyleSheet("border: none;")
        self.attendance_image.setPixmap(QtGui.QPixmap(get_resource_path("take_attd.png")))
        self.attendance_image.setScaledContents(True)
        self.attendance_image.setAlignment(QtCore.Qt.AlignCenter)
        
        # Card description
        self.attendance_desc = QtWidgets.QLabel(self.card_attendance)
        self.attendance_desc.setGeometry(QtCore.QRect(20, 270, 380, 50))
        self.attendance_desc.setFont(create_font("Arial", 10))
        self.attendance_desc.setStyleSheet("color: #666666; border: none;")
        self.attendance_desc.setAlignment(QtCore.Qt.AlignCenter)
        self.attendance_desc.setWordWrap(True)
        self.attendance_desc.setText(
            "Take attendance for your class using face recognition and record timestamps"
        )
        
        # Attendance button
        self.btn_attendance = QtWidgets.QPushButton(self.card_attendance)
        self.btn_attendance.setGeometry(QtCore.QRect(120, 330, 200, 45))
        self.btn_attendance.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_attendance.setText("Take Attendance")
        self.btn_attendance.setStyleSheet("""
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
        
        # Raise elements above image
        self.attendance_image.raise_()
        self.attendance_title.raise_()
        self.attendance_desc.raise_()
        self.btn_attendance.raise_()
    
    def connect_signals(self):
        """Connect button signals to navigation methods."""
        self.btn_register.clicked.connect(self.open_register_face)
        self.btn_attendance.clicked.connect(self.open_login)
    
    def open_register_face(self):
        """Navigate to Register Face window."""
        from RegisterFace_window import RegisterFaceWindow
        self.register_window = RegisterFaceWindow()
        self.register_window.show()
        self.close()
    
    def open_login(self):
        """Navigate to Login window."""
        from Login_window import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = HomeWindow()
    window.show()
    sys.exit(app.exec_())
