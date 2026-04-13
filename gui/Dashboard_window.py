"""
Dashboard Window - Attendance Dashboard for Smart Attendance System
Navigation:
  - "Back" button -> Attendance Window (or previous window)
Displays:
  - Date selector and filters for Class and Subject
  - Attendance statistics (Total, Present, Absent)
  - Attendance table with Student ID, Name, and Status
"""

import os
import sys
from PyQt5 import QtCore, QtGui, QtWidgets

# Add the logic folder to import path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, '..', 'logic'))

from db_config import get_teacher_classes_and_subjects, get_attendance_records, get_sessions_for_filter
from utils import create_font


def get_resource_path(filename):
    """Get the absolute path to a resource file in the script's directory."""
    return os.path.join(SCRIPT_DIR, filename)


class DashboardWindow(QtWidgets.QMainWindow):
    """Dashboard window displaying attendance statistics and records."""
    
    def __init__(self, teacher_id=None, pre_select_class=None, pre_select_subject=None):
        super().__init__()
        self.teacher_id = teacher_id if teacher_id else 'T01'
        self.pre_select_class = pre_select_class
        self.pre_select_subject = pre_select_subject
        self.setup_ui()
        self.load_teacher_data()
        
        # Pre-select class and subject if passed from Attendance Window
        if self.pre_select_class:
            index = self.combo_class.findData(self.pre_select_class)
            if index >= 0:
                self.combo_class.setCurrentIndex(index)
        if self.pre_select_subject:
            index = self.combo_subject.findData(self.pre_select_subject)
            if index >= 0:
                self.combo_subject.setCurrentIndex(index)
                
        self.connect_signals()
        # Initialize fetch after setup
        self.on_primary_filter_changed()
    
    def setup_ui(self):
        """Initialize and configure all UI elements."""
        # Window configuration
        self.setObjectName("DashboardWindow")
        self.resize(788, 728)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowMaximizeButtonHint)
        self.setWindowTitle("Attendance Dashboard")
        
        # Window icon
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(get_resource_path("Logo1.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(icon)
        
        # Central widget
        self.central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        # Main card frame
        self.card_frame = QtWidgets.QFrame(self.central_widget)
        self.card_frame.setGeometry(QtCore.QRect(30, 10, 731, 661))
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
        self.title_label.setGeometry(QtCore.QRect(190, 10, 431, 61))
        self.title_label.setFont(create_font("Segoe UI", 22, bold=True))
        self.title_label.setStyleSheet("border: none;")
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        self.title_label.setText("Attendance Dashboard")
        
        # Filters section
        self._create_filters()
        
        # Statistics cards
        self._create_total_card()
        self._create_present_card()
        self._create_absent_card()
        
        # Attendance table
        self._create_attendance_table()
        
        # Back button
        self._create_back_button()
        
        # Menu and status bars
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 788, 26))
        self.setMenuBar(self.menubar)
        
        self.statusbar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.statusbar)
    


    
    def _create_filters(self):
        """Create date selector and filter combo boxes."""
        # Date selector
        self.date_edit = QtWidgets.QDateEdit(self.card_frame)
        self.date_edit.setGeometry(QtCore.QRect(60, 90, 151, 31))
        self.date_edit.setFont(create_font("Segoe UI", 10))
        self.date_edit.setStyleSheet("border: 1px solid #e0e0e0; border-radius: 4px;")
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QtCore.QDate.currentDate())
        
        # Class selector
        self.combo_class = QtWidgets.QComboBox(self.card_frame)
        self.combo_class.setGeometry(QtCore.QRect(250, 90, 201, 31))
        self.combo_class.setFont(create_font("Segoe UI", 10))
        self.combo_class.setStyleSheet("border: 1px solid #e0e0e0; border-radius: 4px;")
        self.combo_class.addItem("---Select Class---")
        
        # Subject selector
        self.combo_subject = QtWidgets.QComboBox(self.card_frame)
        self.combo_subject.setGeometry(QtCore.QRect(470, 90, 221, 31))
        self.combo_subject.setFont(create_font("Segoe UI", 10))
        self.combo_subject.setStyleSheet("border: 1px solid #e0e0e0; border-radius: 4px;")
        self.combo_subject.addItem("---Select Subject---")
        
        # Session selector
        self.combo_session = QtWidgets.QComboBox(self.card_frame)
        self.combo_session.setGeometry(QtCore.QRect(60, 130, 631, 31))
        self.combo_session.setFont(create_font("Segoe UI", 10))
        self.combo_session.setStyleSheet("border: 1px solid #e0e0e0; border-radius: 4px;")
        self.combo_session.addItem("---Select Session---")
    
    def _create_stat_card(self, x, colors, text):
        """Create a statistics card label with gradient background."""
        label = QtWidgets.QLabel(self.card_frame)
        label.setGeometry(QtCore.QRect(x, 170, 231, 91))
        label.setFont(create_font("Segoe UI", 28, bold=True))
        label.setStyleSheet(f"""
            background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                stop:0 {colors[0]}, stop:1 {colors[1]});
            color: white; border-radius: 8px; border: none;
            font-weight: bold; font-family: Segoe UI; font-size: 28px;
        """)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setText(text)
        return label
    
    def _create_total_card(self):
        """Create the Total students statistics card."""
        self.label_total = self._create_stat_card(10, ("#60a5fa", "#3b82f6"), "Total\n0")
    
    def _create_present_card(self):
        """Create the Present students statistics card."""
        self.label_present = self._create_stat_card(250, ("#2adc4d", "#16a34a"), "Present\n0")
    
    def _create_absent_card(self):
        """Create the Absent students statistics card."""
        self.label_absent = self._create_stat_card(490, ("#ef4444", "#b91c1c"), "Absent\n0")
    
    def _create_attendance_table(self):
        """Create the attendance records table."""
        self.table_widget = QtWidgets.QTableWidget(self.card_frame)
        self.table_widget.setGeometry(QtCore.QRect(20, 280, 691, 281))
        self.table_widget.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e0e0e0;
                border-radius: 0px;
                gridline-color: #e0e0e0;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                border: none;
                border-bottom: 1px solid #e0e0e0;
                padding: 8px;
                font-weight: bold;
                font-family: Segoe UI;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 8px;
            }
        """)
        self.table_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        
        # Configure table
        self.table_widget.setColumnCount(3)
        self.table_widget.setRowCount(0)
        
        # Set headers with font
        header_font = create_font("Segoe UI", 12)
        for col, header_text in enumerate(["Student ID", "Name", "Status"]):
            item = QtWidgets.QTableWidgetItem(header_text)
            item.setFont(header_font)
            self.table_widget.setHorizontalHeaderItem(col, item)
        
        # Configure header
        header = self.table_widget.horizontalHeader()
        header.setCascadingSectionResizes(True)
        header.setDefaultSectionSize(230)
        header.setMinimumSectionSize(50)
        header.setSortIndicatorShown(True)
        header.setStretchLastSection(True)
        
        # Hide row numbers
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.verticalHeader().setCascadingSectionResizes(False)
        self.table_widget.verticalHeader().setHighlightSections(False)
        
        # Selection behavior
        self.table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_widget.setAlternatingRowColors(True)

    def _create_back_button(self):
        """Create the Back button with icon."""
        self.btn_back = QtWidgets.QPushButton(self.card_frame)
        self.btn_back.setGeometry(QtCore.QRect(225, 590, 281, 51))
        self.btn_back.setFont(create_font("Segoe UI", 12, bold=True))
        self.btn_back.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_back.setText("Back to Take Attendance")
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #2adc4d, stop:1 #16a34a);
                color: white;
                border-radius: 16px;
                border: none;
            }
            QPushButton:hover {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #42e660, stop:1 #1eb854);
            }
        """)

    def connect_signals(self):
        """Connect signals to handler methods."""
        self.date_edit.dateChanged.connect(self.on_primary_filter_changed)
        self.combo_class.currentIndexChanged.connect(self.on_primary_filter_changed)
        self.combo_subject.currentIndexChanged.connect(self.on_primary_filter_changed)
        self.combo_session.currentIndexChanged.connect(self.on_session_changed)
        self.btn_back.clicked.connect(self.go_back)

    def load_teacher_data(self):
        """Fetch and populate class/subject dropdowns for the logged-in teacher."""
        data = get_teacher_classes_and_subjects(self.teacher_id)
        if data:
            for cls in data['classes']:
                self.combo_class.addItem(cls['display_name'], cls['class_id'])
            for sub in data['subjects']:
                self.combo_subject.addItem(sub['subject_name'], sub['subject_id'])

    def on_primary_filter_changed(self):
        """Handle changes to Date, Class, or Subject to populate available sessions."""
        class_id = self.combo_class.currentData()
        subject_id = self.combo_subject.currentData()
        date_str = self.date_edit.date().toString('yyyy-MM-dd')

        self.combo_session.blockSignals(True)
        self.combo_session.clear()
        self.combo_session.addItem("---Select Session---")
        
        if class_id and subject_id:
            sessions = get_sessions_for_filter(self.teacher_id, class_id, subject_id, date_str)
            for s in sessions:
                # Format time to HH:MM manually
                st = str(s['start_time']).rsplit(':', 1)[0] if ':' in str(s['start_time']) else str(s['start_time'])
                et = str(s['end_time']).rsplit(':', 1)[0] if ':' in str(s['end_time']) else str(s['end_time'])
                
                # Add human readable session time as text, session_id as data
                self.combo_session.addItem(f"{st} to {et}", s['session_id'])
                
            if sessions:
                # Auto-select the first valid session
                self.combo_session.setCurrentIndex(1)
                
        self.combo_session.blockSignals(False)
        self.on_session_changed()

    def on_session_changed(self):
        """Handle session selection to load the attendance table."""
        class_id = self.combo_class.currentData()
        session_id = self.combo_session.currentData()

        if not class_id or not session_id:
            self.clear_attendance_records()
            self.update_statistics(0, 0, 0)
            return

        records = get_attendance_records(class_id, session_id)
        self.clear_attendance_records()

        total = 0
        present = 0
        absent = 0

        for r in records:
            status = r['status']
            if status.lower() == 'present':
                present += 1
            else:
                absent += 1
            total += 1
            self.add_attendance_record(r['student_id'], r['student_name'], status)

        self.update_statistics(total, present, absent)
    
    def update_statistics(self, total, present, absent):
        """Update the statistics cards with new values."""
        self.label_total.setText(f"Total\n{total}")
        self.label_present.setText(f"Present\n{present}")
        self.label_absent.setText(f"Absent\n{absent}")
    
    def add_attendance_record(self, student_id, name, status):
        """Add a new row to the attendance table."""
        row_position = self.table_widget.rowCount()
        self.table_widget.insertRow(row_position)
        
        # Create items with center alignment
        id_item = QtWidgets.QTableWidgetItem(str(student_id))
        id_item.setTextAlignment(QtCore.Qt.AlignCenter)
        id_item.setFont(create_font("Segoe UI", 10))
        
        name_item = QtWidgets.QTableWidgetItem(name)
        name_item.setTextAlignment(QtCore.Qt.AlignCenter)
        name_item.setFont(create_font("Segoe UI", 10))
        
        status_item = QtWidgets.QTableWidgetItem(status)
        status_item.setTextAlignment(QtCore.Qt.AlignCenter)
        status_item.setFont(create_font("Segoe UI", 10))
        
        # Set status color
        if status.lower() == "present":
            status_item.setForeground(QtGui.QColor("#16a34a"))
        else:
            status_item.setForeground(QtGui.QColor("#b91c1c"))
        
        self.table_widget.setItem(row_position, 0, id_item)
        self.table_widget.setItem(row_position, 1, name_item)
        self.table_widget.setItem(row_position, 2, status_item)
    
    def clear_attendance_records(self):
        """Clear all records from the attendance table."""
        self.table_widget.setRowCount(0)
    
    def go_back(self):
        """Navigate back to the previous window (Attendance)."""
        from Attendance_window import AttendanceWindow
        self.attendance_window = AttendanceWindow(teacher_id=self.teacher_id)
        self.attendance_window.show()
        self.close()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = DashboardWindow()
    window.show()
    sys.exit(app.exec_())
