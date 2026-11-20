from photo_upload import router as photo_router
from pydantic import BaseModel
from typing import Optional
from fastapi import FastAPI
from database import get_db_connection

app = FastAPI(
    title="Smart Attendance Management System",
    description="Attendance Management Backend",
    version="1.0"
)
app.include_router(photo_router)
class Student(BaseModel):
    roll_no: str
    name: str
    section: str
    year: int
    drive_photo_id: Optional[str] = None
    
@app.get("/")
def home():
    return {
        "message": "Smart Attendance Backend is Running!"
    }


@app.get("/test-db")
def test_database():
    connection = get_db_connection()

    if connection is None:
        return {"status": "Database connection failed"}

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT current_database()")
        result = cursor.fetchone()

        cursor.close()

        return {
            "status": "Connected Successfully",
            "database": result[0]
        }

    finally:
        connection.close()

@app.post("/students")
def register_student(student: Student):

    connection = get_db_connection()

    if connection is None:
        return {"error": "Database connection failed"}

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO students
            (roll_no, name, section, year, drive_photo_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING student_id;
            """,
            (
                student.roll_no,
                student.name,
                student.section,
                student.year,
                student.drive_photo_id
            )
        )

        student_id = cursor.fetchone()[0]
        connection.commit()
        cursor.close()

        return {
            "message": "Student registered successfully!",
            "student_id": student_id,
            "roll_no": student.roll_no
        }

    except Exception as error:
        connection.rollback()
        return {"error": str(error)}

    finally:
        connection.close()

@app.get("/students")
def get_students():

    connection = get_db_connection()

    if connection is None:
        return {"error": "Database connection failed"}

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT student_id, roll_no, name, section, year, drive_photo_id
            FROM students
            ORDER BY student_id;
        """)

        rows = cursor.fetchall()

        columns = [description[0] for description in cursor.description]

        students = [
            dict(zip(columns, row))
            for row in rows
        ]

        cursor.close()

        return {
            "total_students": len(students),
            "students": students
        }

    finally:
        connection.close()
