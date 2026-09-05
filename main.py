
# ======================================================
# SENTRIPRINT - BACKEND API
# ======================================================

# FastAPI is the framework we are using to build
# our SentriPrint backend.
from fastapi import FastAPI, HTTPException

# Pydantic is used to define and validate the data
# that our API receives.
from pydantic import BaseModel

# SQLite is the database we are using for SentriPrint.
import sqlite3

# datetime allows us to record the exact time
# an event happens.
from datetime import datetime

# Optional allows some fields to be optional.
from typing import Optional


# ======================================================
# CREATE THE FASTAPI APPLICATION
# ======================================================

# Create our FastAPI application.
#
# IMPORTANT:
# This variable must be called "app".
#
# Uvicorn will look for this variable when we run:
#
# py -m uvicorn main:app --reload

app = FastAPI()


# ======================================================
# DATABASE CONFIGURATION
# ======================================================

# Name of our SQLite database file.
DATABASE = "sentriprint.db"


# ======================================================
# DATABASE SETUP
# ======================================================

def create_database():

    # Connect to the SQLite database.
    #
    # If the database does not exist, SQLite will
    # automatically create it.
    connection = sqlite3.connect(DATABASE)

    # Create a cursor.
    #
    # The cursor is what we use to execute SQL commands.
    cursor = connection.cursor()


    # ==================================================
    # STUDENTS TABLE
    # ==================================================
    #
    # This table contains information about registered
    # students.
    #
    # Example:
    #
    # student_id      CPE/24/001
    # name            John Doe
    # department      Computer Engineering
    # level           200
    # fingerprint_id  1

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


    # ==================================================
    # ATTENDANCE TABLE
    # ==================================================
    #
    # This table stores every time a student records
    # attendance.
    #
    # One student can therefore have MANY attendance
    # records.

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            fingerprint_id INTEGER NOT NULL,
            device_id TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)


    # Save the database changes.
    connection.commit()

    # Close the database connection.
    connection.close()


# Run the database setup when the API starts.
create_database()


# ======================================================
# DATA MODELS
# ======================================================

# ------------------------------------------------------
# STUDENT MODEL
# ------------------------------------------------------
#
# This defines the information required when registering
# a student.

class Student(BaseModel):

    # Student's matriculation/registration number.
    student_id: str

    # Student's full name.
    name: str

    # Student's department.
    # Optional because we may not always have it.
    department: Optional[str] = None

    # Student's academic level.
    # Optional because we may not always have it.
    level: Optional[int] = None

    # ID of the fingerprint stored inside the AS608.
    # Optional during registration for now.
    fingerprint_id: Optional[int] = None


# ------------------------------------------------------
# ATTENDANCE MODEL
# ------------------------------------------------------
#
# This defines the information that will eventually
# be sent by the ESP32 to record attendance.

class Attendance(BaseModel):

    # Student associated with the fingerprint.
    student_id: str

    # Fingerprint ID returned by the fingerprint sensor.
    fingerprint_id: int

    # Unique identifier for the SentriPrint device.
    device_id: str


# ======================================================
# HOME ENDPOINT
# ======================================================

# GET /
#
# This endpoint simply confirms that the API is alive.

@app.get("/")
def home():

    return {
        "message": "SentriPrint API is working"
    }


# ======================================================
# REGISTER A STUDENT
# ======================================================

# POST /students
#
# This endpoint registers a new student in our database.

@app.post("/students")
def register_student(student: Student):

    # Connect to the database.
    connection = sqlite3.connect(DATABASE)

    # Create a cursor.
    cursor = connection.cursor()

    try:

        # Insert the student into the students table.
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

        # Save the changes.
        connection.commit()

        # Return a successful response.
        return {
            "status": "success",
            "message": "Student registered successfully",
            "student_id": student.student_id
        }

    except sqlite3.IntegrityError:

        # This error occurs when a student_id or
        # fingerprint_id already exists.
        raise HTTPException(
            status_code=409,
            detail="Student ID or Fingerprint ID already exists"
        )

    finally:

        # Always close the database connection.
        connection.close()


# ======================================================
# GET ALL STUDENTS
# ======================================================

# GET /students
#
# This endpoint returns every registered student.

@app.get("/students")
def get_students():

    # Connect to the database.
    connection = sqlite3.connect(DATABASE)

    # Create a cursor.
    cursor = connection.cursor()

    # Select all students.
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

    # Retrieve all rows.
    rows = cursor.fetchall()

    # Close the database connection.
    connection.close()


    # Create an empty list for our students.
    students = []


    # Convert each database row into a dictionary.
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


    # Return the students.
    return {
        "status": "success",
        "count": len(students),
        "students": students
    }


# ======================================================
# RECORD ATTENDANCE
# ======================================================

# POST /attendance
#
# This endpoint records attendance.
#
# Eventually, the ESP32 will send this information
# after the AS608 successfully identifies a fingerprint.

@app.post("/attendance")
def record_attendance(attendance: Attendance):

    # Connect to the database.
    connection = sqlite3.connect(DATABASE)

    # Create a cursor.
    cursor = connection.cursor()


    # ==================================================
    # CHECK WHETHER THE STUDENT EXISTS
    # ==================================================

    # Search for the student using their student ID.
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

    # Get the matching student.
    student = cursor.fetchone()


    # If the student doesn't exist, don't record
    # attendance.
    if student is None:

        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Student is not registered"
        )


    # ==================================================
    # CHECK FINGERPRINT
    # ==================================================

    # The fingerprint ID sent by the ESP32 should match
    # the fingerprint ID registered to the student.

    registered_fingerprint_id = student[1]

    if registered_fingerprint_id != attendance.fingerprint_id:

        connection.close()

        raise HTTPException(
            status_code=403,
            detail="Fingerprint does not match student"
        )


    # ==================================================
    # CREATE ATTENDANCE TIMESTAMP
    # ==================================================

    # Record the current date and time.
    timestamp = datetime.now().isoformat()


    # ==================================================
    # INSERT ATTENDANCE RECORD
    # ==================================================

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


    # Save the attendance record.
    connection.commit()

    # Get the ID assigned to this attendance record.
    attendance_id = cursor.lastrowid

    # Close the database connection.
    connection.close()


    # Return a successful response.
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


# ======================================================
# GET ALL ATTENDANCE RECORDS
# ======================================================

# GET /attendance
#
# This endpoint returns all attendance records.

@app.get("/attendance")
def get_attendance():

    # Connect to the database.
    connection = sqlite3.connect(DATABASE)

    # Create a cursor.
    cursor = connection.cursor()


    # Retrieve attendance records.
    #
    # ORDER BY timestamp DESC means the newest
    # attendance records appear first.

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

    # Get all attendance records.
    rows = cursor.fetchall()

    # Close the database connection.
    connection.close()


    # Create an empty list for our records.
    records = []


    # Convert each database row into a dictionary.
    for row in rows:

        records.append({
            "id": row[0],
            "student_id": row[1],
            "fingerprint_id": row[2],
            "device_id": row[3],
            "timestamp": row[4]
        })


    # Return all attendance records.
    return {
        "status": "success",
        "count": len(records),
        "attendance": records
    }