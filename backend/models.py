from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

# Auth models
class LoginRequest(BaseModel):
    id: str
    password: str
    role: str
    company: Optional[str] = None

class UserInfo(BaseModel):
    id: str
    name: str
    role: str
    company: Optional[str] = None

class LoginResponse(BaseModel):
    success: bool
    token: str
    user: UserInfo

# Student models
class StudentProfileUpdate(BaseModel):
    name: str
    dept: str
    year: str
    role: str

class StudentPersonalUpdate(BaseModel):
    email: Optional[str] = ""
    phone: Optional[str] = ""
    dob: Optional[str] = ""
    address: Optional[str] = ""
    guardianName: Optional[str] = ""
    guardianPhone: Optional[str] = ""

class StudentSkillUpdate(BaseModel):
    skill: str
    level: str

class StudentResumeUpdate(BaseModel):
    resumeLink: Optional[str] = ""
    resumeText: Optional[str] = ""

class MockAnswerSubmission(BaseModel):
    answers: Dict[int, int]  # question_idx -> selected_option_idx

# Opening models
class OpeningCreate(BaseModel):
    title: str
    location: str
    type: str
    duration: str
    company: str
    skills: List[str]

# Admin models
class SkillCreate(BaseModel):
    name: str

class SkillRename(BaseModel):
    newName: str

class StudentAccountCreate(BaseModel):
    id: str
    password: str
    name: str
    dept: str
    year: str

class StudentAccountUpdate(BaseModel):
    name: str
    password: str
    dept: str
    year: str

class AdminAccountCreate(BaseModel):
    id: str
    password: str
    name: str

class AdminAccountUpdate(BaseModel):
    name: str
    password: str

class QuestionInput(BaseModel):
    id: Optional[str] = None
    text: str
    options: List[str]
    correct: int

class MockTestCreateOrUpdate(BaseModel):
    title: str
    description: Optional[str] = ""
    questions: List[QuestionInput]
