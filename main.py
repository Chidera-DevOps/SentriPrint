from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from datetime import datetime
from typing import Optional


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(title="SentriPrint API")


# Allow the SentriPrint frontend to communicate with the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

DATABASE = "sentriprint.db"


# =========================================================
# ATTENDANCE SESSION STATE
# =========================================================

# Determines whether an attendance session is currently open.
attendance_active = False

# Stores the time the current attendance session started.
attendance_start_time = None

# Stores the student IDs that have already attended
# during the current attendance session.
current_attendees = set()


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def create_database():
    """
    Create the required database tables if they do not exist.

    IMPORTANT:
    This does NOT delete existing data.
    """

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    # -----------------------------------------------------
    # Students table
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT,
            level INTEGER,
            fingerprint_id INTEGER UNIQUE,
            created_at TEXT NOT NULL
        )
    """)

    # -----------------------------------------------------
    # Attendance table
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            fingerprint_id INTEGER NOT NULL,
            device_id TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


# Create the database/tables when the API starts.
#
# IMPORTANT:
# This does NOT delete existing data.
create_database()


# =========================================================
# PYDANTIC MODELS
# =========================================================

class Student(BaseModel):
    """
    Information required to register a student.
    """

    student_id: str
    name: str
    department: Optional[str] = None
    level: Optional[int] = None
    fingerprint_id: Optional[int] = None


class Attendance(BaseModel):
    """
    Information sent by the ESP32 when a fingerprint
    has been successfully identified.
    """

    # Fingerprint ID returned by the AS608.
    fingerprint_id: int

    # ID of the SentriPrint device.
    device_id: str


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():
    """
    Check whether the SentriPrint API is running.
    """

    return {
        "message": "SentriPrint API is working"
    }


# =========================================================
# START ATTENDANCE
# =========================================================

@app.post("/attendance/start")
def start_attendance():
    """
    Open a new attendance session.
    """

    global attendance_active
    global attendance_start_time
    global current_attendees

    # -----------------------------------------------------
    # Prevent two sessions from being active simultaneously.
    # -----------------------------------------------------

    if attendance_active:

        raise HTTPException(
            status_code=409,
            detail="Attendance is already active"
        )

    # -----------------------------------------------------
    # Open attendance session.
    # -----------------------------------------------------

    attendance_active = True

    # Record session start time.
    attendance_start_time = datetime.now().isoformat()

    # Start with an empty attendee list.
    current_attendees.clear()

    return {
        "status": "success",
        "message": "Attendance started",
        "started_at": attendance_start_time
    }


# =========================================================
# STOP ATTENDANCE
# =========================================================

@app.post("/attendance/stop")
def stop_attendance():
    """
    Close the current attendance session.
    """

    global attendance_active
    global attendance_start_time
    global current_attendees

    # -----------------------------------------------------
    # Make sure a session is currently active.
    # -----------------------------------------------------

    if not attendance_active:

        raise HTTPException(
            status_code=409,
            detail="Attendance is not currently active"
        )

    # -----------------------------------------------------
    # Record stop time.
    # -----------------------------------------------------

    stopped_at = datetime.now().isoformat()

    # Count students who attended.
    total_attendees = len(current_attendees)

    # -----------------------------------------------------
    # Close session.
    # -----------------------------------------------------

    attendance_active = False
    attendance_start_time = None

    # -----------------------------------------------------
    # Clear temporary session list.
    #
    # IMPORTANT:
    # Actual attendance records remain in SQLite.
    # -----------------------------------------------------

    current_attendees.clear()

    return {
        "status": "success",
        "message": "Attendance stopped",
        "stopped_at": stopped_at,
        "total_attendees": total_attendees
    }


# =========================================================
# ATTENDANCE STATUS
# =========================================================

@app.get("/attendance/status")
def attendance_status():
    """
    Check the current attendance session.
    """

    return {
        "status": "success",
        "attendance_active": attendance_active,
        "started_at": attendance_start_time,
        "students_recorded": len(current_attendees)
    }


# =========================================================
# CURRENT ATTENDANCE
# =========================================================

@app.get("/attendance/current")
def get_current_attendance():
    """
    Return attendance records for the current session.

    This uses the student IDs stored in current_attendees
    and retrieves their attendance records from SQLite.
    """

    # -----------------------------------------------------
    # 1. Make sure an attendance session is active.
    # -----------------------------------------------------

    if not attendance_active:

        raise HTTPException(
            status_code=403,
            detail="Attendance is currently closed"
        )

    # -----------------------------------------------------
    # 2. If nobody has attended yet, return an empty list.
    # -----------------------------------------------------

    if not current_attendees:

        return {
            "status": "success",
            "count": 0,
            "attendance": []
        }

    # -----------------------------------------------------
    # 3. Connect to SQLite.
    # -----------------------------------------------------

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    try:

        # -------------------------------------------------
        # Build placeholders for the SQL IN clause.
        # -------------------------------------------------

        placeholders = ",".join(
            ["?"] * len(current_attendees)
        )

        cursor.execute(
            f"""
            SELECT
                id,
                student_id,
                fingerprint_id,
                device_id,
                timestamp
            FROM attendance
            WHERE student_id IN ({placeholders})
            ORDER BY timestamp DESC
            """,
            tuple(current_attendees)
        )

        rows = cursor.fetchall()

    finally:

        connection.close()

    # -----------------------------------------------------
    # 4. Convert database rows into JSON objects.
    # -----------------------------------------------------

    records = []

    for row in rows:

        records.append({
            "id": row[0],
            "student_id": row[1],
            "fingerprint_id": row[2],
            "device_id": row[3],
            "timestamp": row[4]
        })

    # -----------------------------------------------------
    # 5. Return current attendance.
    # -----------------------------------------------------

    return {
        "status": "success",
        "count": len(records),
        "attendance": records
    }


# =========================================================
# RECORD ATTENDANCE
# =========================================================

@app.post("/attendance")
def record_attendance(attendance: Attendance):
    """
    Record attendance using the fingerprint ID.

    Flow:

        AS608
          ↓
        ESP32
          ↓
        fingerprint_id
          ↓
        FastAPI
          ↓
        Find student
          ↓
        Save attendance
    """

    # -----------------------------------------------------
    # 1. Check whether attendance is active.
    # -----------------------------------------------------

    if not attendance_active:

        raise HTTPException(
            status_code=403,
            detail="Attendance is currently closed"
        )

    # -----------------------------------------------------
    # 2. Connect to SQLite.
    # -----------------------------------------------------

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    try:

        # -------------------------------------------------
        # 3. Find student using fingerprint ID.
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                student_id,
                fingerprint_id,
                name
            FROM students
            WHERE fingerprint_id = ?
        """, (
            attendance.fingerprint_id,
        ))

        student = cursor.fetchone()

        # -------------------------------------------------
        # 4. Reject unknown fingerprint.
        # -------------------------------------------------

        if student is None:

            raise HTTPException(
                status_code=404,
                detail="Fingerprint is not registered to a student"
            )

        # -------------------------------------------------
        # Extract student information.
        # -------------------------------------------------

        student_id = student[0]
        fingerprint_id = student[1]
        name = student[2]

        # -------------------------------------------------
        # 5. Prevent duplicate attendance.
        # -------------------------------------------------

        if student_id in current_attendees:

            raise HTTPException(
                status_code=409,
                detail="Student has already recorded attendance for this period"
            )

        # -------------------------------------------------
        # 6. Generate timestamp.
        # -------------------------------------------------

        timestamp = datetime.now().isoformat()

        # -------------------------------------------------
        # 7. Insert attendance record.
        # -------------------------------------------------

        cursor.execute("""
            INSERT INTO attendance (
                student_id,
                fingerprint_id,
                device_id,
                timestamp
            )
            VALUES (?, ?, ?, ?)
        """, (
            student_id,
            fingerprint_id,
            attendance.device_id,
            timestamp
        ))

        # Save the record.
        connection.commit()

        # Get the newly created attendance ID.
        attendance_id = cursor.lastrowid

        # -------------------------------------------------
        # 8. Add student to current session.
        # -------------------------------------------------

        current_attendees.add(student_id)

        # -------------------------------------------------
        # 9. Return successful response.
        # -------------------------------------------------

        return {
            "status": "success",
            "message": "Attendance recorded successfully",
            "attendance_id": attendance_id,
            "student": {
                "student_id": student_id,
                "name": name,
                "fingerprint_id": fingerprint_id
            },
            "device_id": attendance.device_id,
            "timestamp": timestamp
        }

    finally:

        # Always close database connection.
        connection.close()


# =========================================================
# RESET ALL ATTENDANCE
# =========================================================

@app.delete("/attendance/reset")
def reset_attendance():
    """
    Delete ALL stored attendance records.

    IMPORTANT:
    - Students are NOT deleted.
    - Fingerprint registrations are NOT affected.
    - Only the attendance table is cleared.

    This endpoint cannot be used while an attendance
    session is active.
    """

    # -----------------------------------------------------
    # 1. Prevent resetting a live attendance session.
    # -----------------------------------------------------

    if attendance_active:

        raise HTTPException(
            status_code=409,
            detail="Stop the current attendance session before resetting attendance"
        )

    # -----------------------------------------------------
    # 2. Connect to SQLite.
    # -----------------------------------------------------

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    try:

        # -------------------------------------------------
        # Count existing records before deleting them.
        # -------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*)
            FROM attendance
        """)

        deleted_count = cursor.fetchone()[0]

        # -------------------------------------------------
        # Delete all attendance records.
        # -------------------------------------------------

        cursor.execute("""
            DELETE FROM attendance
        """)

        connection.commit()

    finally:

        connection.close()

    # -----------------------------------------------------
    # 3. Reset temporary session state as well.
    # -----------------------------------------------------

    current_attendees.clear()

    return {
        "status": "success",
        "message": "All attendance records have been reset",
        "deleted_count": deleted_count
    }


# =========================================================
# REGISTER STUDENT
# =========================================================

@app.post("/students")
def register_student(student: Student):
    """
    Register a new student.
    """

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO students (
                student_id,
                name,
                department,
                level,
                fingerprint_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            student.student_id,
            student.name,
            student.department,
            student.level,
            student.fingerprint_id,
            datetime.now().isoformat()
        ))

        connection.commit()

        return {
            "status": "success",
            "message": "Student registered successfully",
            "student_id": student.student_id
        }

    except sqlite3.IntegrityError:

        raise HTTPException(
            status_code=409,
            detail="Student ID or Fingerprint ID already exists"
        )

    finally:

        connection.close()


# =========================================================
# GET ALL STUDENTS
# =========================================================

@app.get("/students")
def get_students():
    """
    Return all registered students.
    """

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                student_id,
                name,
                department,
                level,
                fingerprint_id,
                created_at
            FROM students
            ORDER BY id DESC
        """)

        rows = cursor.fetchall()

    finally:

        connection.close()

    students = []

    for row in rows:

        students.append({
            "id": row[0],
            "student_id": row[1],
            "name": row[2],
            "department": row[3],
            "level": row[4],
            "fingerprint_id": row[5],
            "created_at": row[6]
        })

    return {
        "status": "success",
        "count": len(students),
        "students": students
    }


# =========================================================
# GET ATTENDANCE HISTORY
# =========================================================

@app.get("/attendance")
def get_attendance():
    """
    Return all attendance records.

    This includes records from previous attendance sessions.
    """

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                student_id,
                fingerprint_id,
                device_id,
                timestamp
            FROM attendance
            ORDER BY timestamp DESC
        """)

        rows = cursor.fetchall()

    finally:

        connection.close()

    records = []

    for row in rows:

        records.append({
            "id": row[0],
            "student_id": row[1],
            "fingerprint_id": row[2],
            "device_id": row[3],
            "timestamp": row[4]
        })

    return {
        "status": "success",
        "count": len(records),
        "attendance": records
    }