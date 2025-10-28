from pydantic import BaseModel, EmailStr
from typing import List

# --- Transcript Model ---
class TranscriptItem(BaseModel):
    question: str
    answer: str

# --- /generate-questions ---
class QuestionRequest(BaseModel):
    resume_text: str

class QuestionResponse(BaseModel):
    questions: List[str]

# --- /evaluate-interview ---
class EvaluateRequest(BaseModel):
    transcript: List[TranscriptItem]

class EvaluateResponse(BaseModel):
    evaluation: str

# --- /send-email ---
class EmailRequest(BaseModel):
    candidate_resume: str
    evaluation_report: str

class EmailResponse(BaseModel):
    message: str
