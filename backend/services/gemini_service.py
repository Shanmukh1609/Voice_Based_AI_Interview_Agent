import os
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from typing import List, Tuple, Optional, TypedDict
import requests  # <-- Import for making synchronous REST API calls for TTS
import json

# Configure the Gemini API key
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("⚠️ WARNING: GOOGLE_API_KEY not found in environment variables.")
    print("   Please set it in your .env file in the project root.")
else:
    genai.configure(api_key=api_key)

# In services/gemini_service.py (add this new class)

class AnswerSufficiency(TypedDict):
    """Schema for the answer sufficiency check"""
    is_sufficient: bool
    follow_up_question: Optional[str]

# --- Safety Settings ---
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# --- Model Initialization ---
text_model = None
# We do not initialize a tts_model, as the 'genai' library does not support it.
# We will call the TTS REST API directly.

if api_key:
    try:
        # Text generation model
        text_model = genai.GenerativeModel(
            # Using a stable, latest model name
            model_name="gemini-2.5-flash", 
            safety_settings=safety_settings
        )
        
    except Exception as e:
        print(f"⚠️ WARNING: Failed to initialize Gemini models: {e}")
else:
    print("⚠️ WARNING: Models not initialized - GOOGLE_API_KEY not set")

# In services/gemini_service.py (add this new async function)

async def check_answer_sufficiency(question: str, answer: str) -> AnswerSufficiency:
    """
    Checks if an answer is sufficient for the question and generates a follow-up
    if it's not.
    """
    print(f"Checking sufficiency for Q: {question} | A: {answer}")
    
    # Define the generation config to force JSON output
    generation_config = genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema=AnswerSufficiency,
    )

    # Initialize the model (using a model that supports JSON mode, like 1.5 Pro)
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config=generation_config
    )

    prompt = f"""
You are an expert technical interviewer. Evaluate the candidate's answer.

    **Question:** "{question}"
    **Answer:** "{answer}"

    **Task:**
    Determine if the answer is sufficient. 
    - If YES: Set "is_sufficient" to true and "follow_up_question" to null.
    - If NO (vague, incomplete, or completely wrong): Set "is_sufficient" to false and provide a polite, probing "follow_up_question".

    **Output Format:**
    You must respond with a SINGLE JSON object. Do not add markdown formatting like ```json.
    
    Example 1 (Sufficient):
    {{
        "is_sufficient": true,
        "follow_up_question": null
    }}

    Example 2 (Insufficient):
    {{
        "is_sufficient": false,
        "follow_up_question": "Could you elaborate on the specific database schema you used?"
    }} """

    try:
        response = await model.generate_content_async(prompt)
        text_response = response.text.strip()
        # Parse the JSON response
        if text_response.startswith("```json"):
            text_response = text_response[7:]
        if text_response.endswith("```"):
            text_response = text_response[:-3]
            
        response_json = json.loads(text_response)
        
        # Validate and return
        
        is_sufficient = response_json.get("is_sufficient", True)
        follow_up = response_json.get("follow_up_question", None)

        if is_sufficient:
            print("Answer is sufficient.")
            return {"is_sufficient": True, "follow_up_question": None}
        else:
            print(f"Answer is insufficient. Follow-up: {follow_up}")
            return {"is_sufficient": False, "follow_up_question": follow_up}

    except Exception as e:
        print(f"Error checking answer sufficiency: {e}")
        # Fallback: If the check fails, assume the answer is sufficient
        # to avoid breaking the interview flow.
        return {"is_sufficient": True, "follow_up_question": None}

# --- FIXED: Changed to 'def' (synchronous) ---
def generate_questions_from_text(resume_text: str, job_description: str, rag_context: str) -> List[str]:
    """
    Generates interview questions using Gemini. (SYNCHRONOUS)
    """
    if not text_model:
        raise ValueError("Gemini model not initialized. Please check GOOGLE_API_KEY in .env file.")
    # 3. Third question?
    system_prompt = f"""
You are an expert HR manager conducting a technical and behavioral interview. 
Based on the provided resume, job_description, and company facts, generate exactly 1 interview questions.
The questions should be a mix of:
- Resume-specific (e.g., "Tell me about your project X...")
- Behavioral (e.g., "Describe a time when...")
- Role-specific (e.g., "How would you handle Y task...")
- Company-specific (using the provided company facts)

Format the output as a numbered list. Do NOT include any preamble or conclusion.
Example:
1. First question?

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
        # --- FIXED: Changed to 'generate_content' (synchronous) ---
        response = text_model.generate_content(
            [system_prompt, user_prompt],
            generation_config=GenerationConfig(temperature=0.7)
        )
        
        text = response.text
        # Parse the numbered list of questions
        questions = text.split('\n')
        questions = [q.replace(f"{i+1}.", "").strip() for i, q in enumerate(questions) if q]
        
        if not questions:
            raise ValueError("Model did not return any questions.")
        # print(questions)
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

# --- FIXED: Changed to 'def' (synchronous) ---
async def evaluate_transcript(transcript_text: str) -> str: # Made a change
    """
    Evaluates a full interview transcript using Gemini. (SYNCHRONOUS)
    """
    if not text_model:
        raise ValueError("Gemini model not initialized. Please check GOOGLE_API_KEY in .env file.")
    
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
        # --- FIXED: Changed to 'generate_content' (synchronous) ---
        response =  text_model.generate_content(
            [system_prompt, user_prompt],
            generation_config=GenerationConfig(temperature=0.5)
        )
        return response.text
    
    except Exception as e:
        print(f"Error in Gemini evaluation: {e}")
        return f"Error: Could not evaluate transcript. {e}"

# --- FIXED: TTS Function (Synchronous REST API call) ---
async def generate_tts_audio(text_to_speak: str, voice: str = "Kore") -> Tuple[Optional[str], Optional[str]]: # change
    """
    Generates TTS audio using the Gemini API via a direct REST call. (SYNCHRONOUS)
    Returns (base64_audio_data, mime_type)
    """
    print(f"Generating TTS audio for text: {text_to_speak}")
    global api_key
    if not api_key:
        print("Error in TTS: GOOGLE_API_KEY not set.")
        return None, None

    prompt = f"Say in a professional, clear, and neutral tone: {text_to_speak}"
    
    # This is the correct, direct REST API endpoint for this model
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice}
                }
            }
        }
    }

    try:
        # Use a SYNCHRONOUS 'requests.post' call.
        # This will block until the audio is ready, which is
        # correct for a synchronous Streamlit app.
        response = requests.post(url, json=payload, timeout=30)
        
        # Raise an error if the API returned a bad status (e.g., 404, 500)
        response.raise_for_status() 
        
        result = response.json()
        
        if "candidates" in result and len(result["candidates"]) > 0:
            part = result["candidates"][0].get("content", {}).get("parts", [{}])[0]
            inline_data = part.get("inlineData", {})
            audio_data = inline_data.get("data")
            mime_type = inline_data.get("mimeType")
            
            if audio_data and mime_type and mime_type.startswith("audio/"):
                print(f"Generated audio MIME type: {mime_type}")
                return audio_data, mime_type
        
        # If we get here, the response was valid JSON but didn't contain audio
        print(f"Invalid audio response structure from API: {result}")
        raise ValueError("Invalid audio response structure from API.")
            
    except Exception as e:
        print(f"Error in Gemini TTS generation: {e}")
        return None, None