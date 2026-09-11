import sqlite3
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from backend.database import get_db
from backend.auth_helper import require_role
from backend.models import (
    SkillCreate, SkillRename, StudentAccountCreate, StudentAccountUpdate,
    AdminAccountCreate, AdminAccountUpdate, MockTestCreateOrUpdate
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

DEPT_ABBR = {
    "Computer Science (CSE)": "CSE",
    "Information Technology (IT)": "IT",
    "Electronics & Comm. (ECE)": "ECE",
    "Mechanical (MECH)": "MECH",
    "Civil": "Civil",
    "Electrical (EEE)": "EEE"
}

# ================= SKILL CATALOG =================
@router.get("/skills")
def get_skills_catalog(user: dict = Depends(require_role(["admin", "student", "recruiter"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT name FROM skills_catalog ORDER BY id ASC")
    return [row["name"] for row in cursor.fetchall()]

@router.post("/skills")
def add_skill(data: SkillCreate, user: dict = Depends(require_role(["admin"])), db: sqlite3.Connection = Depends(get_db)):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Skill name cannot be empty")
    
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO skills_catalog (name) VALUES (?)", (name,))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="That skill already exists")

    # Add to all existing students as 'Not started'
    cursor.execute("SELECT id FROM users WHERE role = 'student'")
    students = cursor.fetchall()
    for s in students:
        cursor.execute("""
            INSERT OR IGNORE INTO student_skills (student_id, skill_name, proficiency_level)
            VALUES (?, ?, 'Not started')
        """, (s["id"], name))

    db.commit()
    return {"success": True, "message": "Skill added to catalog"}

@router.put("/skills/{old_skill}")
def rename_skill(old_skill: str, data: SkillRename, user: dict = Depends(require_role(["admin"])), db: sqlite3.Connection = Depends(get_db)):
    new_name = data.newName.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="New skill name cannot be empty")
    
    cursor = db.cursor()
    cursor.execute("SELECT id FROM skills_catalog WHERE name = ?", (old_skill,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Skill not found")

    try:
        cursor.execute("UPDATE skills_catalog SET name = ? WHERE name = ?", (new_name, old_skill))
        cursor.execute("UPDATE student_skills SET skill_name = ? WHERE skill_name = ?", (new_name, old_skill))
        cursor.execute("UPDATE opening_skills SET skill_name = ? WHERE skill_name = ?", (new_name, old_skill))
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Skill name already exists")

    return {"success": True, "message": "Skill renamed successfully"}

@router.delete("/skills/{skill_name}")
def delete_skill(skill_name: str, user: dict = Depends(require_role(["admin"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM skills_catalog WHERE name = ?", (skill_name,))
    cursor.execute("DELETE FROM student_skills WHERE skill_name = ?", (skill_name,))
    cursor.execute("DELETE FROM opening_skills WHERE skill_name = ?", (skill_name,))
    db.commit()
    return {"success": True, "message": "Skill deleted successfully"}

# ================= STUDENTS MANAGEMENT =================
@router.get("/students")
def list_students(user: dict = Depends(require_role(["admin"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM skills_catalog")
    total_skills = cursor.fetchone()[0]

    cursor.execute("""
        SELECT u.id, u.name, u.password, p.dept, p.year, p.target_role
        FROM users u
        LEFT JOIN student_profiles p ON u.id = p.student_id
        WHERE u.role = 'student'
        ORDER BY u.id ASC
    """)
    students = cursor.fetchall()
    result = []
    for s in students:
        sid = s["id"]
        cursor.execute("SELECT COUNT(*) FROM student_skills WHERE student_id = ? AND proficiency_level != 'Not started'", (sid,))
        rated = cursor.fetchone()[0]

        cursor.execute("SELECT score, total FROM mock_attempts WHERE student_id = ?", (sid,))
        attempts = cursor.fetchall()
        best_pct = None
        if attempts:
            best_pct = max(round((a["score"] / a["total"]) * 100) for a in attempts)

        result.append({
            "id": s["id"],
            "name": s["name"],
            "pass": s["password"],
            "dept": s["dept"] or "Computer Science (CSE)",
            "deptAbbr": DEPT_ABBR.get(s["dept"], s["dept"] or "CSE"),
            "year": s["year"] or "1st year",
            "role": s["target_role"] or "Backend Developer",
            "ratedSkills": rated,
            "totalSkills": total_skills,
            "bestPct": best_pct
        })
    return result

@router.post("/students")
def create_student(data: StudentAccountCreate, user: dict = Depends(require_role(["admin"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE LOWER(id) = LOWER(?)", (data.id.strip(),))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="That student ID already exists")

    sid = data.id.strip()
    cursor.execute("INSERT INTO users (id, password, role, name) VALUES (?, ?, 'student', ?)",
                   (sid, data.password.strip(), data.name.strip()))
    cursor.execute("""
        INSERT INTO student_profiles (student_id, dept, year, target_role, email, phone, dob, address, guardian_name, guardian_phone, resume_link, resume_text, resume_updated)
        VALUES (?, ?, ?, 'Backend Developer', '', '', '', '', '', '', '', '', '')
    """, (sid, data.dept, data.year))

    # Initialize catalog skills
    cursor.execute("SELECT name FROM skills_catalog")
    for row in cursor.fetchall():
        cursor.execute("INSERT INTO student_skills (student_id, skill_name, proficiency_level) VALUES (?, ?, 'Not started')",
                       (sid, row["name"]))

    db.commit()
    return {"success": True, "message": "Student account created"}

@router.put("/students/{student_id}")
def update_student(student_id: str, data: StudentAccountUpdate, user: dict = Depends(require_role(["admin"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'student'", (student_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Student not found")

    cursor.execute("UPDATE users SET name = ?, password = ? WHERE id = ?",
                   (data.name.strip(), data.password.strip(), student_id))
    cursor.execute("UPDATE student_profiles SET dept = ?, year = ? WHERE student_id = ?",
                   (data.dept, data.year, student_id))
    db.commit()
    return {"success": True, "message": "Student updated successfully"}

@router.delete("/students/{student_id}")
def delete_student(student_id: str, user: dict = Depends(require_role(["admin"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE id = ? AND role = 'student'", (student_id,))
    db.commit()
    return {"success": True, "message": "Student removed successfully"}

# ================= ADMIN ACCOUNTS =================
@router.get("/admins")
def list_admins(user: dict = Depends(require_role(["admin"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, name, password FROM users WHERE role = 'admin' ORDER BY id ASC")
    return [{"id": r["id"], "name": r["name"], "pass": r["password"]} for r in cursor.fetchall()]

@router.post("/admins")
def create_admin(data: AdminAccountCreate, user: dict = Depends(require_role(["admin"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE LOWER(id) = LOWER(?)", (data.id.strip(),))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="That admin ID already exists")

    cursor.execute("INSERT INTO users (id, password, role, name) VALUES (?, ?, 'admin', ?)",
                   (data.id.strip(), data.password.strip(), data.name.strip()))
    db.commit()
    return {"success": True, "message": "Admin added successfully"}

@router.put("/admins/{admin_id}")
def update_admin(admin_id: str, data: AdminAccountUpdate, user: dict = Depends(require_role(["admin"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'admin'", (admin_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Admin not found")

    cursor.execute("UPDATE users SET name = ?, password = ? WHERE id = ?",
                   (data.name.strip(), data.password.strip(), admin_id))
    db.commit()
    return {"success": True, "message": "Admin updated successfully"}

@router.delete("/admins/{admin_id}")
def delete_admin(admin_id: str, user: dict = Depends(require_role(["admin"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    if cursor.fetchone()[0] <= 1:
        raise HTTPException(status_code=400, detail="Cannot remove the only admin account")
    
    if user["id"].lower() == admin_id.lower():
        raise HTTPException(status_code=400, detail="Cannot remove the account you are currently signed in with")

    cursor.execute("DELETE FROM users WHERE id = ? AND role = 'admin'", (admin_id,))
    db.commit()
    return {"success": True, "message": "Admin removed successfully"}

# ================= MOCK TESTS CRUD =================
@router.get("/mock-tests")
def list_admin_mock_tests(user: dict = Depends(require_role(["admin"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, title, description FROM mock_tests ORDER BY created_at ASC")
    tests = cursor.fetchall()
    result = []
    for t in tests:
        tid = t["id"]
        cursor.execute("SELECT id, question_text, options_json, correct_index, sort_order FROM mock_questions WHERE test_id = ? ORDER BY sort_order ASC", (tid,))
        questions = []
        for q in cursor.fetchall():
            questions.append({
                "id": q["id"],
                "text": q["question_text"],
                "options": json.loads(q["options_json"]),
                "correct": q["correct_index"]
            })
        result.append({
            "id": tid,
            "title": t["title"],
            "description": t["description"] or "",
            "questions": questions
        })
    return result

@router.post("/mock-tests")
def create_mock_test(data: MockTestCreateOrUpdate, user: dict = Depends(require_role(["admin"])), db: sqlite3.Connection = Depends(get_db)):
    if not data.title.strip() or not data.questions:
        raise HTTPException(status_code=400, detail="Title and questions are required")
    
    tid = "t-" + uuid.uuid4().hex[:7]
    cursor = db.cursor()
    cursor.execute("INSERT INTO mock_tests (id, title, description) VALUES (?, ?, ?)",
                   (tid, data.title.strip(), (data.description or "").strip()))
    
    for idx, q in enumerate(data.questions):
        qid = "q-" + uuid.uuid4().hex[:7]
        clean_opts = [o.strip() for o in q.options if o.strip()]
        cursor.execute("""
            INSERT INTO mock_questions (id, test_id, question_text, options_json, correct_index, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (qid, tid, q.text.strip(), json.dumps(clean_opts), q.correct, idx))
        
    db.commit()
    return {"success": True, "id": tid, "message": "Mock test created successfully"}

@router.put("/mock-tests/{test_id}")
def update_mock_test(test_id: str, data: MockTestCreateOrUpdate, user: dict = Depends(require_role(["admin"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id FROM mock_tests WHERE id = ?", (test_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Mock test not found")

    cursor.execute("UPDATE mock_tests SET title = ?, description = ? WHERE id = ?",
                   (data.title.strip(), (data.description or "").strip(), test_id))
    
    # Re-create questions
    cursor.execute("DELETE FROM mock_questions WHERE test_id = ?", (test_id,))
    for idx, q in enumerate(data.questions):
        qid = q.id or ("q-" + uuid.uuid4().hex[:7])
        clean_opts = [o.strip() for o in q.options if o.strip()]
        cursor.execute("""
            INSERT INTO mock_questions (id, test_id, question_text, options_json, correct_index, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (qid, test_id, q.text.strip(), json.dumps(clean_opts), q.correct, idx))

    db.commit()
    return {"success": True, "message": "Mock test updated successfully"}

@router.delete("/mock-tests/{test_id}")
def delete_mock_test(test_id: str, user: dict = Depends(require_role(["admin"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM mock_tests WHERE id = ?", (test_id,))
    cursor.execute("DELETE FROM mock_questions WHERE test_id = ?", (test_id,))
    cursor.execute("DELETE FROM mock_attempts WHERE test_id = ?", (test_id,))
    db.commit()
    return {"success": True, "message": "Mock test removed successfully"}
