# ======================================================
# SENTRIPRINT - FIRST API
# ======================================================

# Import FastAPI from the FastAPI package.
#
# FastAPI is the framework we are using to build
# our SentriPrint backend.
from fastapi import FastAPI


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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            fingerprint_id INTEGER NOT NULL,
            device_id TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')

    connection.commit()
    connection.close()

create_database()


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