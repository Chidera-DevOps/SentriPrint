# ======================================================
# SENTRIPRINT - FIRST API
# ======================================================

# Import FastAPI from the FastAPI package.
#
# FastAPI is the framework we are using to build
# our SentriPrint backend.
from fastapi import FastAPI, HTTPException


# ======================================================
# CREATE OUR APPLICATION
# ======================================================

# Create the FastAPI application.
#
# IMPORTANT:
# This variable MUST be called "app".
#
# Uvicorn will look for this variable when we run:
#
# py -m uvicorn main:app --reload

from pydantic import BaseModel

import sqlite3
from datetime import datetime
from typing import Optional
app = FastAPI()


# ======================================================
# FIRST ENDPOINT
# ======================================================

# This tells FastAPI:
#
# "When someone sends a GET request to '/',
# run the home() function."

DATABASE = "sentriprint.db"
def create_database():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT,
            level INTEGER,
            fingerprint_id INTEGER UNIQUE,
            created_at TEXT NOT NULL
        )
    """)

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
    student_id: str

    fingerprint_id: int
    device_id: str

@app.get("/")
def home():

    # Return a Python dictionary.
    #
    # FastAPI automatically converts this into JSON.
    return {
        "message": "SentriPrint API is working"
    }


@app.post("/students")
def register_student(student: Student):

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    try:
        cursor.execute('''
            INSERT INTO attendance (
                student_id,
                name,
                department,
                level,
                fingerprint_id,
                created_at
            ) 
            VALUES (?, ?, ?, ?, ?)
        ''', (
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
        raise HTTPException(status_code=409, detail="Student ID or Fingerprint ID already exists")
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
    """)
    rows = cursor.fetchall()
    connection.close()

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

    students = cursor.fetchall()

    connection.close()

    return {
        "status": "success",
        "data": [
            {
                "id": student[0],
                "student_id": student[1],
                "name": student[2],
                "department": student[3],
                "level": student[4],
                "fingerprint_id": student[5],
                "created_at": student[6]
            } for student in students
        ]
    }


@app.post("/attendance")
def record_attendance(attendance: Attendance):

    connection = sqlite3.connect(DATABASE)

    cursor = connection.cursor()
    timestamp = datetime.now().isoformat()

    cursor.execute('''
        INSERT INTO attendance (
        student_id,
        fingerprint_id,
        device_id,
        timestamp
        )
        values (?, ?, ?, ?)
    ''', (
        attendance.student_id, 
        attendance.fingerprint_id, 
        attendance.device_id, 
        timestamp
    ))

    connection.commit()
    attendance_id = cursor.lastrowid
    connection.close()

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