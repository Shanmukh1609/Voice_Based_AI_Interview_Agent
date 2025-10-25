import os
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from typing import List

# Configure the Gemini API key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- Safety Settings ---
# Block harmful content
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# --- Model Initialization ---
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash-preview-09-2025",
    safety_settings=safety_settings
)

async def generate_questions_from_text(resume_text: str, job_description: str, rag_context: str) -> List[str]:
    """
    Generates interview questions using Gemini.
    """
    
    system_prompt = f"""
You are an expert HR manager conducting a technical and behavioral interview. 
Based on the provided resume, job description, and company facts, generate exactly 5 interview questions.
The questions should be a mix of:
- Resume-specific (e.g., "Tell me about your project X...")
- Behavioral (e.g., "Describe a time when...")
- Role-specific (e.g., "How would you handle Y task...")
- Company-specific (using the provided company facts)

Format the output as a numbered list. Do NOT include any preamble or conclusion.
Example:
1. First question?
2. Second question?
3. Third question?
4. Fourth question?
5. Fifth question?
"""
    
    user_prompt = f"""
--- RESUME ---
{resume_text}

--- JOB DESCRIPTION ---
{job_description}

--- RELEVANT COMPANY FACTS (from RAG) ---
{rag_context or "N/A"}
"""

    try:
        response = await model.generate_content_async(
            [system_prompt, user_prompt],
            generation_config=GenerationConfig(temperature=0.7)
        )
        
        text = response.text
        # Parse the numbered list of questions
        questions = text.split('\n')
        questions = [q.replace(f"{i+1}.", "").strip() for i, q in enumerate(questions) if q]
        
        if not questions:
            raise ValueError("Model did not return any questions.")
            
        return questions

    except Exception as e:
        print(f"Error in Gemini question generation: {e}")
        # Fallback in case of API error
        return [
            "Can you tell me about your most recent project?",
            "What challenges did you face and how did you overcome them?",
            "Why are you interested in this role?",
            "How do you handle working under pressure?",
            "What do you know about our company?"
        ]


async def evaluate_transcript(transcript_text: str) -> str:
    """
    Evaluates a full interview transcript using Gemini.
    """
    
    system_prompt = """
You are a senior hiring manager providing a final evaluation for a job candidate. 
You will be given the full transcript of an AI-conducted interview.
Your task is to provide a comprehensive evaluation of the candidate's performance.

The evaluation report must include the following sections, formatted using Markdown:
- **Overall Summary:** A brief, 2-3 sentence summary of the candidate's performance.
- **Strengths:** A bulleted list of the candidate's strong points.
- **Weaknesses / Areas for Improvement:** A bulleted list of areas where the candidate could improve.
- **Competency Score:** An overall score from 1 to 10 (e.g., **Score: 7.5/10**).

Base your evaluation *only* on the provided transcript. Be critical but fair.
Do not evaluate the AI's questions, only the candidate's answers.
Be concise and professional.
"""
    
    user_prompt = f"""
--- INTERVIEW TRANSCRIPT ---
{transcript_text}

--- END OF TRANSCRIPT ---

Please provide your evaluation now.
"""
    
    try:
        response = await model.generate_content_async(
            [system_prompt, user_prompt],
            generation_config=GenerationConfig(temperature=0.5)
        )
        return response.text
    
    except Exception as e:
        print(f"Error in Gemini evaluation: {e}")
        return f"Error: Could not evaluate transcript. {e}"
