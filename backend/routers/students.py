import sqlite3
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from backend.database import get_db
from backend.auth_helper import require_role
from backend.models import (
    StudentProfileUpdate, StudentPersonalUpdate, StudentSkillUpdate,
    StudentResumeUpdate, MockAnswerSubmission
)

router = APIRouter(prefix="/api/student", tags=["student"])

@router.get("/me")
def get_student_data(user: dict = Depends(require_role(["student"])), db: sqlite3.Connection = Depends(get_db)):
    student_id = user["id"]
    cursor = db.cursor()

    # User & Profile
    cursor.execute("""
        SELECT u.id, u.name, p.dept, p.year, p.target_role, p.email, p.phone, p.dob, p.address,
               p.guardian_name, p.guardian_phone, p.resume_link, p.resume_text, p.resume_updated
        FROM users u
        LEFT JOIN student_profiles p ON u.id = p.student_id
        WHERE u.id = ?
    """, (student_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Student profile not found")

    # Skills
    cursor.execute("SELECT skill_name, proficiency_level FROM student_skills WHERE student_id = ?", (student_id,))
    skills = {r["skill_name"]: r["proficiency_level"] for r in cursor.fetchall()}

    # Also make sure all catalog skills are included
    cursor.execute("SELECT name FROM skills_catalog")
    for cat_row in cursor.fetchall():
        sk_name = cat_row["name"]
        if sk_name not in skills:
            skills[sk_name] = "Not started"

    # Mock attempts (best attempt per test)
    cursor.execute("""
        SELECT test_id, score, total, date 
        FROM mock_attempts 
        WHERE student_id = ? 
        ORDER BY score DESC
    """, (student_id,))
    attempts = {}
    for att in cursor.fetchall():
        tid = att["test_id"]
        if tid not in attempts:
            attempts[tid] = {
                "score": att["score"],
                "total": att["total"],
                "date": att["date"]
            }

    return {
        "id": row["id"],
        "name": row["name"],
        "dept": row["dept"] or "Computer Science (CSE)",
        "year": row["year"] or "1st year",
        "role": row["target_role"] or "Backend Developer",
        "personal": {
            "email": row["email"] or "",
            "phone": row["phone"] or "",
            "dob": row["dob"] or "",
            "address": row["address"] or "",
            "guardianName": row["guardian_name"] or "",
            "guardianPhone": row["guardian_phone"] or ""
        },
        "skills": skills,
        "resumeLink": row["resume_link"] or "",
        "resumeText": row["resume_text"] or "",
        "resumeUpdated": row["resume_updated"] or "",
        "mockAttempts": attempts
    }

@router.put("/me/profile")
def update_profile(data: StudentProfileUpdate, user: dict = Depends(require_role(["student"])), db: sqlite3.Connection = Depends(get_db)):
    student_id = user["id"]
    cursor = db.cursor()

    cursor.execute("UPDATE users SET name = ? WHERE id = ?", (data.name.strip(), student_id))
    cursor.execute("""
        UPDATE student_profiles 
        SET dept = ?, year = ?, target_role = ? 
        WHERE student_id = ?
    """, (data.dept, data.year, data.role, student_id))
    db.commit()
    return {"success": True, "message": "Profile updated"}

@router.put("/me/personal")
def update_personal(data: StudentPersonalUpdate, user: dict = Depends(require_role(["student"])), db: sqlite3.Connection = Depends(get_db)):
    student_id = user["id"]
    cursor = db.cursor()

    cursor.execute("""
        UPDATE student_profiles 
        SET email = ?, phone = ?, dob = ?, address = ?, guardian_name = ?, guardian_phone = ?
        WHERE student_id = ?
    """, (data.email.strip(), data.phone.strip(), data.dob, data.address.strip(),
          data.guardianName.strip(), data.guardianPhone.strip(), student_id))
    db.commit()
    return {"success": True, "message": "Personal details saved"}

@router.put("/me/skill")
def update_skill(data: StudentSkillUpdate, user: dict = Depends(require_role(["student"])), db: sqlite3.Connection = Depends(get_db)):
    student_id = user["id"]
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO student_skills (student_id, skill_name, proficiency_level)
        VALUES (?, ?, ?)
        ON CONFLICT(student_id, skill_name) DO UPDATE SET proficiency_level = excluded.proficiency_level
    """, (student_id, data.skill, data.level))
    db.commit()
    return {"success": True, "message": "Skill updated"}

@router.put("/me/resume")
def update_resume(data: StudentResumeUpdate, user: dict = Depends(require_role(["student"])), db: sqlite3.Connection = Depends(get_db)):
    student_id = user["id"]
    cursor = db.cursor()
    now_str = datetime.now().strftime("%d %b %Y")

    cursor.execute("""
        UPDATE student_profiles 
        SET resume_link = ?, resume_text = ?, resume_updated = ?
        WHERE student_id = ?
    """, (data.resumeLink.strip(), data.resumeText.strip(), now_str, student_id))
    db.commit()
    return {"success": True, "message": "Resume saved", "resumeUpdated": now_str}

@router.get("/me/mock-tests")
def get_mock_tests(user: dict = Depends(require_role(["student"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, title, description FROM mock_tests")
    tests = []
    for row in cursor.fetchall():
        tid = row["id"]
        # count questions
        cursor.execute("SELECT COUNT(*) FROM mock_questions WHERE test_id = ?", (tid,))
        q_count = cursor.fetchone()[0]
        tests.append({
            "id": tid,
            "title": row["title"],
            "description": row["description"] or "",
            "questionCount": q_count
        })
    return tests

@router.get("/me/mock-tests/{test_id}")
def get_mock_test_questions(test_id: str, user: dict = Depends(require_role(["student"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, title, description FROM mock_tests WHERE id = ?", (test_id,))
    test = cursor.fetchone()
    if not test:
        raise HTTPException(status_code=404, detail="Mock test not found")

    cursor.execute("""
        SELECT id, question_text, options_json, sort_order 
        FROM mock_questions 
        WHERE test_id = ? 
        ORDER BY sort_order ASC
    """, (test_id,))
    questions = []
    for q in cursor.fetchall():
        opts = json.loads(q["options_json"])
        questions.append({
            "id": q["id"],
            "text": q["question_text"],
            "options": opts
        })
    
    return {
        "id": test["id"],
        "title": test["title"],
        "description": test["description"] or "",
        "questions": questions
    }

@router.post("/me/mock-tests/{test_id}/submit")
def submit_mock_test(test_id: str, submission: MockAnswerSubmission, user: dict = Depends(require_role(["student"])), db: sqlite3.Connection = Depends(get_db)):
    student_id = user["id"]
    cursor = db.cursor()
    
    cursor.execute("SELECT id, title FROM mock_tests WHERE id = ?", (test_id,))
    test = cursor.fetchone()
    if not test:
        raise HTTPException(status_code=404, detail="Mock test not found")

    cursor.execute("""
        SELECT id, correct_index, sort_order 
        FROM mock_questions 
        WHERE test_id = ? 
        ORDER BY sort_order ASC
    """, (test_id,))
    questions = cursor.fetchall()
    
    total = len(questions)
    if total == 0:
        raise HTTPException(status_code=400, detail="Test has no questions")

    score = 0
    for idx, q in enumerate(questions):
        selected = submission.answers.get(idx)
        if selected is not None and selected == q["correct_index"]:
            score += 1

    date_str = datetime.now().strftime("%d %b %Y")
    cursor.execute("""
        INSERT INTO mock_attempts (student_id, test_id, score, total, date)
        VALUES (?, ?, ?, ?, ?)
    """, (student_id, test_id, score, total, date_str))
    db.commit()

    pct = round((score / total) * 100)
    return {
        "success": True,
        "score": score,
        "total": total,
        "percentage": pct,
        "date": date_str
    }
