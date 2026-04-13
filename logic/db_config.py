import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager
import bcrypt

# ──────────────────────────────────────────────
# 1. DATABASE CONNECTION
# ──────────────────────────────────────────────
def get_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',               # ← change to your MySQL username
            password='root',   # ← change to your MySQL password
            database='smart_attendance'          # ← change to your database name
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Database connection error: {e}")
        return None

@contextmanager
def db_cursor(dictionary=True):
    """Context manager that handles connection, cursor, and cleanup.
    
    Usage:
        with db_cursor() as (cursor, connection):
            cursor.execute("SELECT ...")
            return cursor.fetchall()
    """
    connection = get_connection()
    if connection is None:
        raise ConnectionError("Database connection failed")
    try:
        cursor = connection.cursor(dictionary=dictionary)
        yield cursor, connection
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# ──────────────────────────────────────────────
# 2. TEACHER AUTHENTICATION
# ──────────────────────────────────────────────
def authenticate_teacher(username, password):
    try:
        with db_cursor() as (cursor, conn):
            cursor.execute(
                "SELECT teacher_id, teacher_name, password FROM teachers WHERE username = %s",
                (username,)
            )
            result = cursor.fetchone()
            
            if result:
                db_hash = result['password']
                try:
                    if bcrypt.checkpw(password.encode('utf-8'), db_hash.encode('utf-8')):
                        return {'teacher_id': result['teacher_id'], 'teacher_name': result['teacher_name']}
                except ValueError:
                    # Fallback for plain-text passwords (if migration hasn't run yet)
                    if password == db_hash:
                        return {'teacher_id': result['teacher_id'], 'teacher_name': result['teacher_name']}
            return None
    except Exception as e:
        print(f"Authentication error: {e}")
        return None

def verify_student_exists(student_id):
    try:
        with db_cursor() as (cursor, conn):
            cursor.execute("SELECT student_id, student_name FROM students WHERE student_id = %s", (student_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"Student verification error: {e}")
        return None

# ──────────────────────────────────────────────
# 3. STUDENT AUTHENTICATION (for face registration)
# ──────────────────────────────────────────────
def authenticate_student(student_id, password):
    """Authenticate a student using student_id and password.
    Returns dict {'student_id', 'student_name'} on success, or None on failure.
    """
    try:
        with db_cursor() as (cursor, conn):
            cursor.execute(
                "SELECT student_id, student_name, password FROM students WHERE student_id = %s",
                (student_id,)
            )
            result = cursor.fetchone()
            
            if result:
                db_hash = result['password']
                try:
                    if bcrypt.checkpw(password.encode('utf-8'), db_hash.encode('utf-8')):
                        return {'student_id': result['student_id'], 'student_name': result['student_name']}
                except ValueError:
                    if password == db_hash:
                        return {'student_id': result['student_id'], 'student_name': result['student_name']}
            return None
    except Exception as e:
        print(f"Student authentication error: {e}")
        return None

def save_face_embedding(student_id, embedding_bytes):
    """Save or UPDATE face embedding for a student."""
    try:
        with db_cursor(dictionary=False) as (cursor, conn):
            # Upsert: INSERT new or UPDATE existing embedding
            # Note: Database MUST already have `UNIQUE INDEX uq_student_id (student_id)` configured
            cursor.execute("""
                INSERT INTO face_embeddings (student_id, embedding) 
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE embedding = VALUES(embedding)
            """, (student_id, embedding_bytes))
            conn.commit()
            return True
    except Exception as e:
        print(f"Save embedding error: {e}")
        return False

# ──────────────────────────────────────────────
# 4. FETCH TEACHER'S CLASSES & SUBJECTS
# ──────────────────────────────────────────────
def get_teacher_classes_and_subjects(teacher_id):
    try:
        with db_cursor() as (cursor, conn):
            # Fetch classes
            cursor.execute("""
                SELECT DISTINCT c.class_id, d.dept_code, sem.sem_no, sec.section_name
                FROM teacher_subject_class tsc
                JOIN classes c ON tsc.class_id = c.class_id
                JOIN departments d ON c.dept_id = d.dept_id
                JOIN semesters sem ON c.sem_id = sem.sem_id
                JOIN sections sec ON c.section_id = sec.section_id
                WHERE tsc.teacher_id = %s
            """, (teacher_id,))
            classes = [
                {'class_id': row['class_id'], 'display_name': f"{row['dept_code']}-{row['sem_no']}{row['section_name']}"}
                for row in cursor.fetchall()
            ]
            
            # Fetch subjects
            cursor.execute("""
                SELECT DISTINCT s.subject_id, s.subject_name
                FROM teacher_subject_class tsc
                JOIN subjects s ON tsc.subject_id = s.subject_id
                WHERE tsc.teacher_id = %s
            """, (teacher_id,))
            subjects = [
                {'subject_id': row['subject_id'], 'subject_name': row['subject_name']}
                for row in cursor.fetchall()
            ]
            
            return {'classes': classes, 'subjects': subjects}
    except Exception as e:
        print(f"Fetch teacher data error: {e}")
        return None

# ──────────────────────────────────────────────
# 5. FACE EMBEDDING RETRIEVAL (for attendance)
# ──────────────────────────────────────────────
def get_face_embeddings_by_class(class_id):
    """Get all face embeddings + student info for a specific class."""
    try:
        with db_cursor() as (cursor, conn):
            cursor.execute("""
                SELECT fe.student_id, fe.embedding, s.student_name
                FROM face_embeddings fe
                JOIN students s ON fe.student_id = s.student_id
                WHERE s.class_id = %s
            """, (class_id,))
            return cursor.fetchall()
    except Exception as e:
        print(f"Fetch face embeddings error: {e}")
        return []

# ──────────────────────────────────────────────
# 6. ATTENDANCE SESSION & RECORDS
# ──────────────────────────────────────────────
def create_attendance_session(teacher_id, subject_id, class_id,
                              session_date, start_time, end_time):
    """Create a new attendance session or return existing one."""
    try:
        with db_cursor() as (cursor, conn):
            # Check if session already exists
            cursor.execute("""
                SELECT session_id FROM attendance_sessions
                WHERE teacher_id = %s AND subject_id = %s AND class_id = %s
                  AND session_date = %s AND start_time = %s AND end_time = %s
            """, (teacher_id, subject_id, class_id, session_date, start_time, end_time))
            existing = cursor.fetchone()
            
            if existing:
                return existing['session_id']
            
            # Create new session (MySQL automatically handles the auto-increment)
            cursor.execute("""
                INSERT INTO attendance_sessions
                (teacher_id, subject_id, class_id, session_date, start_time, end_time)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (teacher_id, subject_id, class_id, session_date, start_time, end_time))
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"Create attendance session error: {e}")
        return None


def mark_attendance(session_id, student_id, status='Present'):
    """Mark attendance for a student in a session. (Status column removed)"""
    try:
        with db_cursor() as (cursor, conn):
            cursor.execute(
                "SELECT student_id FROM attendance_records WHERE session_id = %s AND student_id = %s",
                (session_id, student_id)
            )
            existing = cursor.fetchone()
            
            if not existing:
                cursor.execute(
                    "INSERT INTO attendance_records (session_id, student_id) VALUES (%s, %s)",
                    (session_id, student_id)
                )
            conn.commit()
            return True
    except Exception as e:
        print(f"Mark attendance error: {e}")
        return False

# ──────────────────────────────────────────────
# 7. DASHBOARD LOGIC
# ──────────────────────────────────────────────
def get_sessions_for_filter(teacher_id, class_id, subject_id, date_str):
    """Fetch available sessions for a given date, class, and subject."""
    try:
        with db_cursor() as (cursor, conn):
            cursor.execute("""
                SELECT session_id, start_time, end_time 
                FROM attendance_sessions 
                WHERE teacher_id = %s AND class_id = %s AND subject_id = %s AND session_date = %s
                ORDER BY start_time ASC
            """, (teacher_id, class_id, subject_id, date_str))
            return cursor.fetchall()
    except Exception as e:
        print(f"Get sessions error: {e}")
        return []

def get_attendance_records(class_id, session_id):
    """Fetch all students for a class and their attendance status for a specific session."""
    try:
        with db_cursor() as (cursor, conn):
            # Get all students for the class
            cursor.execute("SELECT student_id, student_name FROM students WHERE class_id = %s", (class_id,))
            students = cursor.fetchall()

            if not session_id:
                return []

            # Check attendance
            # Since 'status' column is removed, presence in the table implies 'Present'
            cursor.execute("SELECT student_id FROM attendance_records WHERE session_id = %s", (session_id,))
            
            present_students = set(str(row['student_id']).strip().upper() for row in cursor.fetchall())

            return [
                {'student_id': s['student_id'], 'student_name': s['student_name'],
                 'status': 'Present' if str(s['student_id']).strip().upper() in present_students else 'Absent'}
                for s in students
            ]
    except Exception as e:
        print(f"Get attendance records error: {e}")
        return []
