import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional
from backend.database import get_db
from backend.models import LoginRequest, LoginResponse, UserInfo
from backend.auth_helper import create_session, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, password, role, name, company FROM users WHERE LOWER(id) = LOWER(?) AND role = ?",
                   (req.id.strip(), req.role.strip()))
    user = cursor.fetchone()
    
    if not user or user["password"] != req.password.strip():
        raise HTTPException(status_code=401, detail="Invalid ID or password")
    
    user_dict = dict(user)
    
    # If recruiter specified a company, update it
    if req.role == "recruiter" and req.company:
        db.execute("UPDATE users SET company = ? WHERE id = ?", (req.company.strip(), user_dict["id"]))
        db.commit()
        user_dict["company"] = req.company.strip()

    token = create_session(db, user_dict["id"], user_dict["role"])
    
    return LoginResponse(
        success=True,
        token=token,
        user=UserInfo(
            id=user_dict["id"],
            name=user_dict["name"],
            role=user_dict["role"],
            company=user_dict.get("company")
        )
    )

@router.get("/me", response_model=UserInfo)
def get_me(user: dict = Depends(get_current_user)):
    return UserInfo(
        id=user["id"],
        name=user["name"],
        role=user["role"],
        company=user.get("company")
    )

@router.post("/logout")
def logout(authorization: Optional[str] = Header(None), db: sqlite3.Connection = Depends(get_db)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        db.execute("DELETE FROM sessions WHERE token = ?", (token,))
        db.commit()
    return {"success": True, "message": "Logged out successfully"}
