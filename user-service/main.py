from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import mysql.connector
import os
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="User Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "user-db"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "database": os.getenv("DB_NAME", "userdb"),
}


def get_db():
    retries = 5
    for i in range(retries):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            return conn
        except Exception as e:
            if i < retries - 1:
                time.sleep(3)
            else:
                raise e


class UserCreate(BaseModel):
    name: str
    email: str
    phone: str


class UserUpdate(BaseModel):
    name: str = None
    email: str = None
    phone: str = None


@app.on_event("startup")
async def startup():
    time.sleep(5)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            phone VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Insert sample data
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    if count == 0:
        sample_users = [
            ("Alice Johnson", "alice@example.com", "+1234567890"),
            ("Bob Smith", "bob@example.com", "+0987654321"),
            ("Carol White", "carol@example.com", "+1122334455"),
        ]
        cursor.executemany(
            "INSERT INTO users (name, email, phone) VALUES (%s, %s, %s)",
            sample_users
        )
    conn.commit()
    cursor.close()
    conn.close()
    logger.info("User service started successfully")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "user-service"}


@app.get("/users")
def get_users():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"users": users}


@app.get("/users/{user_id}")
def get_user(user_id: int):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/users", status_code=201)
def create_user(user: UserCreate):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, phone) VALUES (%s, %s, %s)",
            (user.name, user.email, user.phone)
        )
        conn.commit()
        user_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return {"id": user_id, "message": "User created successfully"}
    except mysql.connector.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already exists")


@app.put("/users/{user_id}")
def update_user(user_id: int, user: UserUpdate):
    conn = get_db()
    cursor = conn.cursor()
    updates = []
    values = []
    if user.name:
        updates.append("name = %s")
        values.append(user.name)
    if user.email:
        updates.append("email = %s")
        values.append(user.email)
    if user.phone:
        updates.append("phone = %s")
        values.append(user.phone)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    values.append(user_id)
    cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = %s", values)
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "User updated successfully"}


@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "User deleted successfully"}
