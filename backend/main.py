import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.database import init_db
from backend.routers import auth, students, recruiters, admin

# Initialize DB
init_db()

app = FastAPI(
    title="Confluence — Academia-Industry Collaboration Portal API",
    description="REST backend for Confluence Portal with SQLite database persistence",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(students.router)
app.include_router(recruiters.router)
app.include_router(admin.router)

# Mount frontend
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

@app.get("/")
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Confluence API is running. Visit /docs for OpenAPI documentation."}

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "confluence-backend"}
