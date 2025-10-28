import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv

# Import utility and service modules
from models.api_models import (
    QuestionRequest, QuestionResponse, 
    EvaluateRequest, EvaluateResponse, 
    EmailRequest, EmailResponse
)
from utils.resume_parser import parse_resume_pdf
# Import the file reader
from utils.file_reader import read_text_file 
from services.rag_service import create_rag_chain, query_rag_chain
from services.gemini_service import generate_questions_from_text, evaluate_transcript
from utils.send_email import send_evaluation_email

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Voice AI Interview Agent Backend",
    description="Handles resume parsing, RAG, question generation, and evaluation."
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins (for local development)
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (GET, POST, etc.)
    allow_headers=["*"], # Allow all headers
)

# --- State ---
# We now load JD, company facts, and HR email into the app's state
app.state.rag_chain = None
app.state.job_description = ""
app.state.company_facts = ""
app.state.hr_email = ""


# --- Endpoints ---

@app.on_event("startup")
async def startup_event():
    """
    On startup, load API keys, file data, and env vars into app state.
    """
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY environment variable not set.")
    
    # Load HR Email from .env
    app.state.hr_email = os.getenv("HR_EMAIL")
    if not app.state.hr_email:
        raise RuntimeError("HR_EMAIL environment variable not set.")
        
    # Load Job Description from file
    app.state.job_description = read_text_file("data/job_description.txt")
    if not app.state.job_description:
        raise RuntimeError("Could not load data/job_description.txt.")
        
    # Load Company Facts from file
    app.state.company_facts = read_text_file("data/company_facts.txt")
    if not app.state.company_facts:
        print("Warning: Could not load data/company_facts.txt. RAG context will be empty.")
        
    print("Server started. GOOGLE_API_KEY, HR_EMAIL, and data files loaded.")


@app.get("/")
def read_root():
    return {"message": "Voice AI Interview Agent Backend is running."}

@app.post("/upload-resume", response_model=dict)
async def upload_resume(file: UploadFile = File(...)):
    """
    Endpoint to upload a resume PDF and parse it.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")
    
    try:
        contents = await file.read()
        resume_text = parse_resume_pdf(contents)
        if not resume_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF. The PDF might be image-based or empty.")
        
        return {"resume_text": resume_text}
    
    except Exception as e:
        print(f"Error parsing resume: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {str(e)}")

@app.post("/generate-questions", response_model=QuestionResponse)
async def generate_questions_endpoint(request: QuestionRequest = Body(...)):
    """
    Generates interview questions based on resume and data loaded from server files.
    """
    try:
        # 1. Create RAG chain from company facts (loaded on startup)
        print("Creating RAG chain...")
        app.state.rag_chain = create_rag_chain(app.state.company_facts)
        
        # 2. Get RAG context (if any)
        rag_context = query_rag_chain(
            app.state.rag_chain,
            f"Facts about our company relevant to a {app.state.job_description}"
        )

        # 3. Generate questions
        print("Generating questions...")
        questions = await generate_questions_from_text(
            request.resume_text,
            app.state.job_description,
            rag_context
        )
        
        return QuestionResponse(questions=questions)
        
    except Exception as e:
        print(f"Error generating questions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate questions: {str(e)}")

@app.post("/evaluate-interview", response_model=EvaluateResponse)
async def evaluate_interview_endpoint(request: EvaluateRequest = Body(...)):
    """
    Evaluates the complete interview transcript.
    """
    try:
        print("Evaluating transcript...")
        transcript_text = "\n\n".join(
            [f"Question {i+1}: {item.question}\nAnswer {i+1}: {item.answer}" 
             for i, item in enumerate(request.transcript)]
        )
        
        evaluation = await evaluate_transcript(transcript_text)
        
        return EvaluateResponse(evaluation=evaluation)
        
    except Exception as e:
        print(f"Error evaluating transcript: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to evaluate transcript: {str(e)}")

@app.post("/send-email", response_model=EmailResponse)
async def send_email_endpoint(request: EmailRequest = Body(...)):
    """
    Sends the evaluation report to the HR email loaded from .env.
    """
    try:
        hr_email = app.state.hr_email
        if not hr_email:
            raise HTTPException(status_code=500, detail="HR Email is not configured on the server.")

        print(f"Sending email to {hr_email}...")
        
        success = send_evaluation_email(
            recipient_email=hr_email,
            candidate_resume=request.candidate_resume,
            evaluation_report=request.evaluation_report
        )
        
        if success:
            return EmailResponse(message="Email sent successfully.")
        else:
            raise HTTPException(status_code=500, detail="Failed to send email. Check SMTP server configuration.")
            
    except Exception as e:
        print(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
