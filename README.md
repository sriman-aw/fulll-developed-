# Confluence — Academia–Industry Collaboration Portal

A full-stack web application featuring an asynchronous **FastAPI** backend and **SQLite** database powering the **Confluence** collaboration portal for Students, Recruiters, and Institution Administrators.

---

## Quick Start

### 1. Requirements
Ensure Python 3.10+ is installed. Dependencies:
```bash
pip install -r requirements.txt
```
*(FastAPI and Uvicorn will be installed)*

### 2. Run the Server
From the `confluence-portal` directory, run:
```bash
python run.py
```

Open your browser to:
- **Web Application**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive API Documentation (Swagger/OpenAPI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Default Demo Credentials

The database (`confluence.db`) is automatically initialized and seeded on first run with demo accounts:

| Role | Login ID | Password | Notes |
|---|---|---|---|
| **Student** | `S001` | `student123` | Priya N. (CSE, 3rd yr) |
| **Student** | `S002` | `student123` | Arjun K. (CSE, 4th yr) |
| **Student** | `S003` | `student123` | Divya S. (IT, 3rd yr) |
| **Recruiter** | `recruiter` | `recruit2026` | Company: *Fintech Solutions Pvt Ltd* |
| **Admin** | `admin` | `admin2026` | Institution Administrator |

---

## Architecture & Features

### 1. Database Schema (`confluence.db`)
- **`users`**: Authentication table with role-based access (`student`, `recruiter`, `admin`).
- **`student_profiles`**: Academic info, contact details, guardian info, resume link & text.
- **`skills_catalog`**: Master skills recognized across the institution.
- **`student_skills`**: Student ratings (`Not started`, `Learning`, `Confident`, `Strong`).
- **`openings` & `opening_skills`**: Recruiter job openings and required skill sets.
- **`mock_tests` & `mock_questions`**: Mock tests managed by administrators.
- **`mock_attempts`**: Student mock test submissions, scores, and dates.
- **`sessions`**: Bearer token session authentication.

### 2. API Endpoints
- **Authentication**: `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`
- **Student Portal**:
  - `GET /api/student/me`: Load profile, skills, test history
  - `PUT /api/student/me/profile`: Update name, department, year, role
  - `PUT /api/student/me/personal`: Update email, phone, address, guardian info
  - `PUT /api/student/me/skill`: Update skill self-assessment
  - `PUT /api/student/me/resume`: Save resume link and summary text
  - `GET /api/student/me/mock-tests`: List available mock tests
  - `POST /api/student/me/mock-tests/{id}/submit`: Submit answers and get instant scoring
- **Recruiter Portal**:
  - `GET /api/recruiter/metrics`: Active openings, candidates count, top match %
  - `GET /api/recruiter/candidates`: Candidate pool dynamically sorted by skill match %
  - `POST /api/recruiter/openings`: Publish new opening
- **Admin Console**:
  - `GET /api/admin/skills`, `POST`, `PUT`, `DELETE`: Full skills catalog management
  - `GET /api/admin/students`, `POST`, `PUT`, `DELETE`: Student accounts management
  - `GET /api/admin/admins`, `POST`, `PUT`, `DELETE`: Admin credentials management
  - `GET /api/admin/mock-tests`, `POST`, `PUT`, `DELETE`: Mock tests & questions creator
