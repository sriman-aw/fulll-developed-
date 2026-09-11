import uuid
import sqlite3
from fastapi import Header, HTTPException, Depends
from typing import Optional
from backend.database import get_db

def create_session(conn: sqlite3.Connection, user_id: str, role: str) -> str:
    token = uuid.uuid4().hex
    conn.execute("INSERT INTO sessions (token, user_id, role) VALUES (?, ?, ?)", (token, user_id, role))
    conn.commit()
    return token

def get_current_user(authorization: Optional[str] = Header(None), db: sqlite3.Connection = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication token required")
    
    token = authorization.split(" ")[1]
    cursor = db.cursor()
    cursor.execute("""
        SELECT u.id, u.name, u.role, u.company 
        FROM sessions s 
        JOIN users u ON s.user_id = u.id 
        WHERE s.token = ?
    """, (token,))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return dict(user)

def require_role(allowed_roles: list):
    def role_checker(user: dict = Depends(get_current_user)):
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden for this role")
        return user
    return role_checker
