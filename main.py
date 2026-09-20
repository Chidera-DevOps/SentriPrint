from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
from datetime import datetime
from typing import Optional

app = FastAPI()

DATABASE = "sentriprint.db"

# Tracks whether an attendance period is currently open.
attendance_active = False

# Stores when the current attendance period started.
attendance_start_time = None

# Stores students who have already attended in the
# current attendance period to prevent duplicates.
current_attendees = set()


def create_database():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    # Stores registered students and their fingerprints.
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

    # Stores attendance records.
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


create_database()


class Student(BaseModel):
    student_id: str
    name: str
    department: Optional[str] = None
    level: Optional[int] = None
    fingerprint_id: Optional[int] = None


class Attendance(BaseModel):
    # The fingerprint ID returned by the AS608.
    fingerprint_id: int

    # Identifies which SentriPrint device sent the scan.
    device_id: str

@app.get("/")
def home():
    return {
        "message": "SentriPrint API is working"
    }


@app.post("/attendance/start")
def start_attendance():
    global attendance_active
    global attendance_start_time
    global current_attendees

    if attendance_active:
        raise HTTPException(
            status_code=409,
            detail="Attendance is already active"
        )

    attendance_active = True
    attendance_start_time = datetime.now().isoformat()

    # Start a fresh attendance period.
    current_attendees.clear()

    return {
        "status": "success",
        "message": "Attendance started",
        "started_at": attendance_start_time
    }

@app.post("/attendance/stop")
def stop_attendance():
    global attendance_active
    global attendance_start_time
    global current_attendees

    # Make sure there is an active attendance session to stop.
    if not attendance_active:
        raise HTTPException(
            status_code=409,
            detail="Attendance is not currently active"
        )

    stopped_at = datetime.now().isoformat()

    # Count everyone who attended this session.
    total_attendees = len(current_attendees)

    # Close the attendance session.
    attendance_active = False
    attendance_start_time = None

    # Clear the temporary attendee list.
    # The actual attendance records remain safely stored
    # in the SQLite database.
    current_attendees.clear()

    return {
        "status": "success",
        "message": "Attendance stopped",
        "stopped_at": stopped_at,
        "total_attendees": total_attendees
    }


@app.post("/attendance")
def record_attendance(attendance: Attendance):

    # ---------------------------------------------------------
    # 1. Make sure an attendance session is currently active.
    # ---------------------------------------------------------
    if not attendance_active:
        raise HTTPException(
            status_code=403,
            detail="Attendance is currently closed"
        )

    # ---------------------------------------------------------
    # 2. Connect to the database.
    # ---------------------------------------------------------
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    try:

        # -----------------------------------------------------
        # 3. Find the student associated with this fingerprint.
        #
        # The ESP32 does NOT send the student's ID.
        # It only sends the fingerprint ID returned by AS608.
        # -----------------------------------------------------
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

        # -----------------------------------------------------
        # 4. If no student is associated with that fingerprint,
        # reject the attendance attempt.
        # -----------------------------------------------------
        if student is None:
            raise HTTPException(
                status_code=404,
                detail="Fingerprint is not registered to a student"
            )

        student_id = student[0]
        fingerprint_id = student[1]
        name = student[2]

        # -----------------------------------------------------
        # 5. Prevent the same student from recording attendance
        # twice during the same attendance session.
        # -----------------------------------------------------
        if student_id in current_attendees:
            raise HTTPException(
                status_code=409,
                detail="Student has already recorded attendance for this period"
            )

        # -----------------------------------------------------
        # 6. Create the attendance timestamp.
        # -----------------------------------------------------
        timestamp = datetime.now().isoformat()

        # -----------------------------------------------------
        # 7. Save the attendance record.
        # -----------------------------------------------------
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

        connection.commit()

        attendance_id = cursor.lastrowid

        # -----------------------------------------------------
        # 8. Mark this student as present for the current
        # attendance session.
        # -----------------------------------------------------
        current_attendees.add(student_id)

        # -----------------------------------------------------
        # 9. Return the student's information to the ESP32.
        # -----------------------------------------------------
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
        connection.close()

@app.get("/attendance/status")
def attendance_status():
    return {
        "status": "success",
        "attendance_active": attendance_active,
        "started_at": attendance_start_time,
        "students_recorded": len(current_attendees)
    }


@app.post("/students")
def register_student(student: Student):
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


@app.get("/students")
def get_students():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

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


@app.post("/attendance")
def record_attendance(attendance: Attendance):

    # Attendance can only be recorded during an
    # active attendance period.
    if not attendance_active:
        raise HTTPException(
            status_code=403,
            detail="Attendance is currently closed"
        )

    # Prevent the same student from attending twice
    # during the current attendance period.
    if attendance.student_id in current_attendees:
        raise HTTPException(
            status_code=409,
            detail="Student has already recorded attendance for this period"
        )

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            student_id,
            fingerprint_id,
            name
        FROM students
        WHERE student_id = ?
    """, (
        attendance.student_id,
    ))

    student = cursor.fetchone()

    if student is None:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Student is not registered"
        )

    # Verify that the fingerprint belongs to the student.
    registered_fingerprint_id = student[1]

    if registered_fingerprint_id != attendance.fingerprint_id:
        connection.close()

        raise HTTPException(
            status_code=403,
            detail="Fingerprint does not match student"
        )

    timestamp = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO attendance (
            student_id,
            fingerprint_id,
            device_id,
            timestamp
        )
        VALUES (?, ?, ?, ?)
    """, (
        attendance.student_id,
        attendance.fingerprint_id,
        attendance.device_id,
        timestamp
    ))

    connection.commit()

    attendance_id = cursor.lastrowid

    connection.close()

    # Mark the student as present for this period.
    current_attendees.add(attendance.student_id)

    return {
        "status": "success",
        "message": "Attendance recorded successfully",
        "attendance_id": attendance_id,
        "data": {
            "student_id": attendance.student_id,
            "fingerprint_id": attendance.fingerprint_id,
            "device_id": attendance.device_id,
            "timestamp": timestamp
        }
    }


@app.get("/attendance")
def get_attendance():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

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