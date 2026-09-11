import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db

def run_tests():
    print("Testing Confluence backend and database...")
    init_db()
    client = TestClient(app)

    # 1. Health check & landing
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[PASS] Health check OK")

    res = client.get("/")
    assert res.status_code == 200, f"Root serve failed: {res.text}"
    assert "Confluence" in res.text, "Index HTML not returned properly"
    print("[PASS] Static index.html served at root OK")

    # 2. Student flow
    login_res = client.post("/api/auth/login", json={
        "id": "S001",
        "password": "student123",
        "role": "student"
    })
    assert login_res.status_code == 200, f"Student login failed: {login_res.text}"
    student_token = login_res.json()["token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}
    print("[PASS] Student login OK")

    # Get student profile
    me_res = client.get("/api/student/me", headers=student_headers)
    assert me_res.status_code == 200, f"Student /me failed: {me_res.text}"
    stu_data = me_res.json()
    assert stu_data["id"] == "S001"
    assert "skills" in stu_data
    print(f"[PASS] Student data loaded: {stu_data['name']}, {len(stu_data['skills'])} skills")

    # Update skill
    skill_update = client.put("/api/student/me/skill", headers=student_headers, json={
        "skill": "System design",
        "level": "Learning"
    })
    assert skill_update.status_code == 200, f"Skill update failed: {skill_update.text}"
    print("[PASS] Student skill update OK")

    # Submit mock test
    submit_res = client.post("/api/student/me/mock-tests/t-dsa/submit", headers=student_headers, json={
        "answers": {0: 1, 1: 1, 2: 0} # All 3 correct
    })
    assert submit_res.status_code == 200, f"Mock test submit failed: {submit_res.text}"
    test_result = submit_res.json()
    assert test_result["score"] == 3
    assert test_result["percentage"] == 100
    print(f"[PASS] Mock test submission OK (Score: {test_result['score']}/{test_result['total']})")

    # 3. Recruiter flow
    rec_login = client.post("/api/auth/login", json={
        "id": "recruiter",
        "password": "recruit2026",
        "role": "recruiter",
        "company": "Fintech Solutions Pvt Ltd"
    })
    assert rec_login.status_code == 200, f"Recruiter login failed: {rec_login.text}"
    rec_token = rec_login.json()["token"]
    rec_headers = {"Authorization": f"Bearer {rec_token}"}
    print("[PASS] Recruiter login OK")

    # Check candidates
    cand_res = client.get("/api/recruiter/candidates", headers=rec_headers)
    assert cand_res.status_code == 200, f"Recruiter candidates failed: {cand_res.text}"
    candidates = cand_res.json()
    assert len(candidates) >= 3
    print(f"[PASS] Recruiter candidates pool loaded: top candidate is {candidates[0]['name']} with {candidates[0]['matchScore']}% match")

    # Post opening
    post_res = client.post("/api/recruiter/openings", headers=rec_headers, json={
        "title": "Cloud Infrastructure Intern",
        "location": "Bengaluru",
        "type": "Internship",
        "duration": "3 months",
        "company": "Fintech Solutions Pvt Ltd",
        "skills": ["Cloud deployment (AWS)", "System design"]
    })
    assert post_res.status_code == 200, f"Post opening failed: {post_res.text}"
    print("[PASS] Recruiter post opening OK")

    # 4. Admin flow
    admin_login = client.post("/api/auth/login", json={
        "id": "admin",
        "password": "admin2026",
        "role": "admin"
    })
    assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
    admin_token = admin_login.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("[PASS] Admin login OK")

    # Add skill to catalog
    add_sk = client.post("/api/admin/skills", headers=admin_headers, json={"name": "Kubernetes & Docker"})
    assert add_sk.status_code == 200, f"Add skill failed: {add_sk.text}"
    print("[PASS] Admin add skill to catalog OK")

    # List students
    students_res = client.get("/api/admin/students", headers=admin_headers)
    assert students_res.status_code == 200, f"Admin list students failed: {students_res.text}"
    students_list = students_res.json()
    assert len(students_list) >= 3
    print(f"[PASS] Admin list students OK ({len(students_list)} students registered)")

    print("\nALL BACKEND & DATABASE TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
