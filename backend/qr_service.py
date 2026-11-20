
import qrcode
import hashlib
import secrets
from datetime import datetime, timedelta
from database import get_db_connection


def generate_qr_session(class_id, classroom_latitude,
                         classroom_longitude, allowed_radius_m=100):

    connection = get_db_connection()

    if connection is None:
        return {"error": "Database connection failed"}

    try:
        cursor = connection.cursor()

        # Generate a secure random token
        token = secrets.token_urlsafe(32)

        # Store only the token hash in database
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        valid_from = datetime.now()
        expires_at = valid_from + timedelta(minutes=2)

        cursor.execute(
            """
            INSERT INTO qr_sessions
            (class_id, token_hash, valid_from, expires_at,
             classroom_latitude, classroom_longitude, allowed_radius_m)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING session_id;
            """,
            (
                class_id,
                token_hash,
                valid_from,
                expires_at,
                classroom_latitude,
                classroom_longitude,
                allowed_radius_m
            )
        )

        session_id = cursor.fetchone()[0]
        connection.commit()

        # Generate QR image
        qr_data = f"{session_id}:{token}"

        qr = qrcode.make(qr_data)
        qr.save(f"attendance_qr_{session_id}.png")

        cursor.close()

        return {
            "message": "QR session created successfully",
            "session_id": session_id,
            "expires_at": expires_at.isoformat(),
            "qr_image": f"attendance_qr_{session_id}.png"
        }

    except Exception as error:
        connection.rollback()
        return {"error": str(error)}

    finally:
        connection.close()

