
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    try:
        connection = psycopg2.connect(
            host="localhost",
            database="smart_attendance",
            user="postgres",
            password=os.getenv("DB_PASSWORD"),
            port="5432"
        )

        print("PostgreSQL Connected Successfully!")
        return connection

    except Exception as error:
        print("Database Connection Failed:", error)
        return None


if __name__ == "__main__":
    connection = get_db_connection()

    if connection:
        connection.close()
        print("Connection Closed Successfully!")
