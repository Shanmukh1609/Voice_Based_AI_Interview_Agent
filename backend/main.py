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
# Allows the frontend (running on a different port) to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins (for local development)
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (GET, POST, etc.)
    allow_headers=["*"], # Allow all headers
)

# --- State ---
# In a production app, you'd use a database (e.g., Firestore) to store this
# For this example, we'll hold the RAG chain in memory
app.state.rag_chain = None

# --- Endpoints ---

@app.on_event("startup")
async def startup_event():
    """
    On startup, check for the Google API key.
    We don't build the RAG chain here, as it's company-specific.
    """
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY environment variable not set.")
    print("Server started. GOOGLE_API_KEY loaded.")

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
        # The parse_resume_pdf function expects bytes
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
    Generates interview questions based on resume, job description, and company facts.
    This endpoint also builds the RAG chain for the session.
    """
    try:
        # 1. Create RAG chain from company facts
        # This will be used to inject company-specific context into the questions
        print("Creating RAG chain...")
        app.state.rag_chain = create_rag_chain(request.company_facts)
        
        # 2. Get RAG context (if any)
        # We can do a quick query to see if any facts are relevant to the job
        rag_context = query_rag_chain(
            app.state.rag_chain,
            f"Facts about our company relevant to a {request.job_description}"
        )

        # 3. Generate questions
        print("Generating questions...")
        questions = await generate_questions_from_text(
            request.resume_text,
            request.job_description,
            rag_context # Pass the RAG context to the question generator
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
        # Format the transcript for the LLM
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
    Sends the evaluation report to a specified HR email.
    """
    try:
        print(f"Sending email to {request.hr_email}...")
        
        success = send_evaluation_email(
            recipient_email=request.hr_email,
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

# --- Run the app ---
if __name__ == "__main__":
    """
    Run the server using uvicorn.
    'main:app' refers to the 'app' instance in the 'main.py' file.
    --reload watches for file changes and restarts the server.
    """
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
