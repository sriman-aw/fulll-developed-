import sqlite3
import json
import os
from pathlib import Path
from typing import Generator

DB_PATH = Path(__file__).resolve().parent.parent / "confluence.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create tables
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        name TEXT NOT NULL,
        company TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS student_profiles (
        student_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        dept TEXT,
        year TEXT,
        target_role TEXT,
        email TEXT,
        phone TEXT,
        dob TEXT,
        address TEXT,
        guardian_name TEXT,
        guardian_phone TEXT,
        resume_link TEXT,
        resume_text TEXT,
        resume_updated TEXT
    );

    CREATE TABLE IF NOT EXISTS skills_catalog (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS student_skills (
        student_id TEXT REFERENCES users(id) ON DELETE CASCADE,
        skill_name TEXT NOT NULL,
        proficiency_level TEXT DEFAULT 'Not started',
        PRIMARY KEY (student_id, skill_name)
    );

    CREATE TABLE IF NOT EXISTS openings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        location TEXT NOT NULL,
        engagement_type TEXT NOT NULL,
        duration TEXT NOT NULL,
        company TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS opening_skills (
        opening_id INTEGER REFERENCES openings(id) ON DELETE CASCADE,
        skill_name TEXT NOT NULL,
        PRIMARY KEY (opening_id, skill_name)
    );

    CREATE TABLE IF NOT EXISTS mock_tests (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS mock_questions (
        id TEXT PRIMARY KEY,
        test_id TEXT REFERENCES mock_tests(id) ON DELETE CASCADE,
        question_text TEXT NOT NULL,
        options_json TEXT NOT NULL,
        correct_index INTEGER NOT NULL,
        sort_order INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS mock_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT REFERENCES users(id) ON DELETE CASCADE,
        test_id TEXT REFERENCES mock_tests(id) ON DELETE CASCADE,
        score INTEGER NOT NULL,
        total INTEGER NOT NULL,
        date TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
        role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Check if database already has users
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        seed_initial_data(conn)

    conn.commit()
    conn.close()

def seed_initial_data(conn: sqlite3.Connection):
    cursor = conn.cursor()

    # 1. Users
    cursor.execute("INSERT INTO users (id, password, role, name) VALUES (?, ?, ?, ?)",
                   ("admin", "admin2026", "admin", "Institution Admin"))
    cursor.execute("INSERT INTO users (id, password, role, name, company) VALUES (?, ?, ?, ?, ?)",
                   ("recruiter", "recruit2026", "recruiter", "Recruiter Account", "Fintech Solutions Pvt Ltd"))

    students_data = [
        ("S001", "student123", "Priya N.", "Computer Science (CSE)", "3rd year", "Backend Developer", "priya.n@example.edu"),
        ("S002", "student123", "Arjun K.", "Computer Science (CSE)", "4th year", "Backend Developer", ""),
        ("S003", "student123", "Divya S.", "Information Technology (IT)", "3rd year", "Frontend Developer", "")
    ]

    for sid, spass, sname, dept, year, role, email in students_data:
        cursor.execute("INSERT INTO users (id, password, role, name) VALUES (?, ?, ?, ?)",
                       (sid, spass, "student", sname))
        cursor.execute("""
            INSERT INTO student_profiles (student_id, dept, year, target_role, email, phone, dob, address, guardian_name, guardian_phone, resume_link, resume_text, resume_updated)
            VALUES (?, ?, ?, ?, ?, '', '', '', '', '', '', '', '')
        """, (sid, dept, year, role, email))

    # 2. Skills Catalog
    catalog_skills = [
        "Data structures & algorithms",
        "SQL & database design",
        "REST APIs",
        "System design",
        "Client communication",
        "Cloud deployment (AWS)"
    ]
    for skill in catalog_skills:
        cursor.execute("INSERT INTO skills_catalog (name) VALUES (?)", (skill,))

    # 3. Student Skills
    student_skill_ratings = {
        "S001": {
            "Data structures & algorithms": "Strong",
            "SQL & database design": "Strong",
            "System design": "Not started",
            "Client communication": "Learning",
            "Cloud deployment (AWS)": "Not started",
            "REST APIs": "Learning"
        },
        "S002": {
            "Data structures & algorithms": "Strong",
            "SQL & database design": "Confident",
            "System design": "Confident",
            "Client communication": "Not started",
            "Cloud deployment (AWS)": "Learning",
            "REST APIs": "Confident"
        },
        "S003": {
            "Data structures & algorithms": "Confident",
            "SQL & database design": "Learning",
            "System design": "Not started",
            "Client communication": "Strong",
            "Cloud deployment (AWS)": "Not started",
            "REST APIs": "Learning"
        }
    }

    for sid, ratings in student_skill_ratings.items():
        for sk, lvl in ratings.items():
            cursor.execute("INSERT INTO student_skills (student_id, skill_name, proficiency_level) VALUES (?, ?, ?)",
                           (sid, sk, lvl))

    # 4. Mock Tests & Questions
    cursor.execute("INSERT INTO mock_tests (id, title, description) VALUES (?, ?, ?)",
                   ("t-dsa", "DSA Fundamentals", "Arrays, complexity, and core data structures"))

    questions = [
        ("q1", "t-dsa", "What is the time complexity of binary search on a sorted array?", ["O(n)", "O(log n)", "O(n log n)", "O(1)"], 1, 0),
        ("q2", "t-dsa", "Which data structure uses LIFO order?", ["Queue", "Stack", "Linked list", "Graph"], 1, 1),
        ("q3", "t-dsa", "What does SQL stand for?", ["Structured Query Language", "Simple Query Logic", "Server Query Language", "Standard Question Language"], 0, 2)
    ]
    for qid, tid, qtext, qopts, correct, order in questions:
        cursor.execute("""
            INSERT INTO mock_questions (id, test_id, question_text, options_json, correct_index, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (qid, tid, qtext, json.dumps(qopts), correct, order))

    # 5. Opening
    cursor.execute("""
        INSERT INTO openings (title, location, engagement_type, duration, company)
        VALUES (?, ?, ?, ?, ?)
    """, ("Backend Developer Intern", "Chennai / Hybrid", "Internship", "6 months", "Fintech Solutions Pvt Ltd"))
    opening_id = cursor.lastrowid

    for sk in ["Data structures & algorithms", "SQL & database design", "REST APIs"]:
        cursor.execute("INSERT INTO opening_skills (opening_id, skill_name) VALUES (?, ?)", (opening_id, sk))

    conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database initialized and seeded.")
