
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from drive_service import get_drive_service
from database import get_db_connection
from googleapiclient.http import MediaIoBaseUpload
import psycopg2
import io

router = APIRouter()

# Google Drive section folder IDs
SECTION_FOLDERS = {
    "A": "1V6HUgPmZ7ay5_Kl991MfatLNALREyOjs",
    "B": "1R-S7RMCVItN96W4V5lNPTATXOAYTL9ls"
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/register-student")
async def register_student(
    roll_no: str = Form(...),
    name: str = Form(...),
    section: str = Form(...),
    year: int = Form(...),
    file: UploadFile = File(...)
):

    roll_no = roll_no.strip()
    name = name.strip()
    section = section.strip().upper()

    if not roll_no or not name:
        raise HTTPException(
            status_code=400,
            detail="Roll number and name are required"
        )

    if section not in SECTION_FOLDERS:
        raise HTTPException(
            status_code=400,
            detail="Section must be A or B"
        )

    if year <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid academic year"
        )

    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(
            status_code=400,
            detail="Only JPG and PNG images allowed"
        )

    content = await file.read(MAX_FILE_SIZE + 1)

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Empty image file"
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Image size must not exceed 5 MB"
        )

    if file.content_type == "image/jpeg":
        valid_image = content.startswith(b"\xff\xd8\xff")
    else:
        valid_image = content.startswith(
            b"\x89PNG\r\n\x1a\n"
        )

    if not valid_image:
        raise HTTPException(
            status_code=400,
            detail="Invalid image content"
        )

    connection = get_db_connection()

    if connection is None:
        raise HTTPException(
            status_code=500,
            detail="Database connection failed"
        )

    uploaded_file_id = None
    cursor = None

    try:
        cursor = connection.cursor()

        # Check duplicate roll number
        cursor.execute(
            "SELECT student_id FROM students WHERE roll_no = %s",
            (roll_no,)
        )

        if cursor.fetchone():
            raise HTTPException(
                status_code=409,
                detail="Roll number already registered"
            )

        # Connect to personal Google Drive
        service = get_drive_service()

        # Upload photo to selected section folder
        media = MediaIoBaseUpload(
            io.BytesIO(content),
            mimetype=file.content_type,
            resumable=True
        )

        file_metadata = {
            "name": f"{roll_no}_{file.filename}",
            "parents": [SECTION_FOLDERS[section]]
        }

        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name"
        ).execute()

        uploaded_file_id = uploaded_file["id"]

        # Save student and Drive photo ID in PostgreSQL
        cursor.execute(
            """
            INSERT INTO students
            (roll_no, name, section, year, drive_photo_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING student_id;
            """,
            (
                roll_no,
                name,
                section,
                year,
                uploaded_file_id
            )
        )

        student_id = cursor.fetchone()[0]

        connection.commit()

        return {
            "message": "Student registered successfully!",
            "student_id": student_id,
            "roll_no": roll_no,
            "name": name,
            "section": section,
            "year": year,
            "drive_photo_id": uploaded_file_id,
            "photo_name": uploaded_file["name"]
        }

    except HTTPException:
        connection.rollback()
        raise

    except psycopg2.errors.UniqueViolation:
        connection.rollback()
        raise HTTPException(
            status_code=409,
            detail="Roll number already registered"
        )

    except Exception as error:
        connection.rollback()

        # Remove uploaded photo if database registration fails
        if uploaded_file_id:
            try:
                service.files().delete(
                    fileId=uploaded_file_id
                ).execute()
            except Exception as cleanup_error:
                print("Drive cleanup failed:", cleanup_error)

        raise HTTPException(
            status_code=500,
            detail=f"Student registration failed: {str(error)}"
        )

    finally:
        if cursor:
            cursor.close()

        connection.close()
