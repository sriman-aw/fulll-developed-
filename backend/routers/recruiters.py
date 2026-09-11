import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict
from backend.database import get_db
from backend.auth_helper import require_role
from backend.models import OpeningCreate

router = APIRouter(prefix="/api/recruiter", tags=["recruiter"])

COMPANY_SKILLS = {
    "Fintech Solutions Pvt Ltd": ["Data structures & algorithms", "SQL & database design", "System design", "Cloud deployment (AWS)"],
    "CloudNet Technologies": ["Cloud deployment (AWS)", "System design", "REST APIs"],
    "BuildRight Infrastructure": ["Client communication", "System design"],
    "Other": []
}

SKILL_LEVEL_WEIGHTS = {
    "Not started": 0.0,
    "Learning": 0.5,
    "Confident": 0.75,
    "Strong": 1.0
}

DEPT_ABBR = {
    "Computer Science (CSE)": "CSE",
    "Information Technology (IT)": "IT",
    "Electronics & Comm. (ECE)": "ECE",
    "Mechanical (MECH)": "MECH",
    "Civil": "Civil",
    "Electrical (EEE)": "EEE"
}

@router.get("/company-skills")
def get_company_skills(user: dict = Depends(require_role(["recruiter"]))):
    return COMPANY_SKILLS

@router.get("/openings")
def list_openings(user: dict = Depends(require_role(["recruiter", "admin", "student"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT id, title, location, engagement_type, duration, company 
        FROM openings 
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    result = []
    for r in rows:
        cursor.execute("SELECT skill_name FROM opening_skills WHERE opening_id = ?", (r["id"],))
        skills = [s["skill_name"] for s in cursor.fetchall()]
        result.append({
            "id": r["id"],
            "title": r["title"],
            "location": r["location"],
            "type": r["engagement_type"],
            "duration": r["duration"],
            "company": r["company"],
            "skills": skills
        })
    return result

@router.post("/openings")
def create_opening(opening: OpeningCreate, user: dict = Depends(require_role(["recruiter", "admin"])), db: sqlite3.Connection = Depends(get_db)):
    if not opening.title.strip() or not opening.skills:
        raise HTTPException(status_code=400, detail="Title and at least one skill are required")

    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO openings (title, location, engagement_type, duration, company)
        VALUES (?, ?, ?, ?, ?)
    """, (opening.title.strip(), opening.location.strip(), opening.type, opening.duration.strip(), opening.company.strip()))
    opening_id = cursor.lastrowid

    for sk in opening.skills:
        cursor.execute("INSERT INTO opening_skills (opening_id, skill_name) VALUES (?, ?)", (opening_id, sk.strip()))

    db.commit()
    return {"success": True, "id": opening_id, "message": "Opening published successfully"}

@router.get("/candidates")
def list_candidates(opening_id: Optional[int] = None, user: dict = Depends(require_role(["recruiter", "admin"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()

    # Determine opening skills
    req_skills = []
    if opening_id:
        cursor.execute("SELECT skill_name FROM opening_skills WHERE opening_id = ?", (opening_id,))
        req_skills = [r["skill_name"] for r in cursor.fetchall()]
    else:
        # Pick the latest opening
        cursor.execute("SELECT id FROM openings ORDER BY id DESC LIMIT 1")
        latest = cursor.fetchone()
        if latest:
            cursor.execute("SELECT skill_name FROM opening_skills WHERE opening_id = ?", (latest["id"],))
            req_skills = [r["skill_name"] for r in cursor.fetchall()]

    # Fetch total skills in catalog for denominator
    cursor.execute("SELECT COUNT(*) FROM skills_catalog")
    catalog_total = cursor.fetchone()[0]

    # Fetch all students
    cursor.execute("""
        SELECT u.id, u.name, p.dept, p.year, p.target_role 
        FROM users u 
        JOIN student_profiles p ON u.id = p.student_id 
        WHERE u.role = 'student'
    """)
    students = cursor.fetchall()

    candidate_results = []
    for s in students:
        sid = s["id"]
        cursor.execute("SELECT skill_name, proficiency_level FROM student_skills WHERE student_id = ?", (sid,))
        skill_rows = cursor.fetchall()
        student_skills = {r["skill_name"]: r["proficiency_level"] for r in skill_rows}

        rated_count = sum(1 for v in student_skills.values() if v != "Not started")

        # Calculate match percentage
        if req_skills:
            total_weight = sum(SKILL_LEVEL_WEIGHTS.get(student_skills.get(sk, "Not started"), 0.0) for sk in req_skills)
            score_pct = round((total_weight / len(req_skills)) * 100)
        else:
            score_pct = 0

        candidate_results.append({
            "id": s["id"],
            "name": s["name"],
            "dept": s["dept"],
            "deptAbbr": DEPT_ABBR.get(s["dept"], s["dept"]),
            "year": s["year"],
            "role": s["target_role"],
            "ratedSkills": rated_count,
            "catalogTotal": catalog_total,
            "matchScore": score_pct
        })

    candidate_results.sort(key=lambda c: c["matchScore"], reverse=True)
    return candidate_results

@router.get("/metrics")
def get_recruiter_metrics(user: dict = Depends(require_role(["recruiter", "admin"])), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
    candidate_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM openings")
    opening_count = cursor.fetchone()[0]

    # Calculate best match
    candidates = list_candidates(user=user, db=db)
    top_match = candidates[0]["matchScore"] if candidates else 0

    return {
        "candidateCount": candidate_count,
        "openingCount": opening_count,
        "topMatch": top_match
    }
