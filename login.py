from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import mysql.connector
import logging

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database connection
def get_db_connection():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="your_username",
            password="your_password",
            database="your_database"
        )
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

# Pydantic model for login request
class LoginRequest(BaseModel):
    username: str
    password: str

# Login endpoint
@app.post("/login")
async def login(login_data: LoginRequest):
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Query to check if the employee exists
        query = """
        SELECT emp_id, emp_name, job_title 
        FROM employee 
        WHERE username = %s AND passwords = %s
        """
        cursor.execute(query, (login_data.username, login_data.password))
        employee = cursor.fetchone()

        if not employee:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # Close the database connection
        cursor.close()
        db.close()

        # Return employee data
        return {
            "emp_id": employee["emp_id"],
            "emp_name": employee["emp_name"],
            "job_title": employee["job_title"]
        }

    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
