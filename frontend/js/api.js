// This file now calls our local backend, not the Gemini API directly.

const BACKEND_URL = "http://127.0.0.1:8000";

/**
 * Helper function to handle fetch responses
 */
async function handleResponse(response) {
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    return response.json();
}

/**
 * Uploads the resume PDF to the backend for parsing.
 * @param {File} file - The resume PDF file.
 * @returns {Promise<object>} - The response containing parsed text.
 */
export async function uploadResume(file) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${BACKEND_URL}/upload-resume`, {
        method: 'POST',
        body: formData,
    });
    return handleResponse(response);
}

/**
 * Calls the backend to generate questions.
 * @param {string} resume_text - Parsed resume text.
 * @returns {Promise<object>} - The response containing the list of questions.
 */
export async function getQuestions(resume_text) {
    // Payload no longer includes job_description or company_facts
    const payload = {
        resume_text,
    };

    const response = await fetch(`${BACKEND_URL}/generate-questions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    return handleResponse(response);
}

/**
 * Calls the backend to evaluate the interview transcript.
 * @param {Array<object>} transcript - The list of {question, answer} pairs.
 * @returns {Promise<object>} - The response containing the evaluation.
 */
export async function evaluateInterview(transcript) {
    const payload = { transcript };

    const response = await fetch(`${BACKEND_URL}/evaluate-interview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    return handleResponse(response);
}

/**
 * Calls the backend to send the evaluation email.
 * @param {string} candidate_resume - The parsed resume text.
 * @param {string} evaluation_report - The final evaluation report.
 * @returns {Promise<object>} - The response confirming email status.
 */
export async function sendEmail(candidate_resume, evaluation_report) {
    // Payload no longer includes hr_email
    const payload = {
        candidate_resume,
        evaluation_report,
    };

    const response = await fetch(`${BACKEND_URL}/send-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    return handleResponse(response);
}


// --- TTS is still handled by the browser-based Gemini API ---
// This keeps the voice interaction fast and avoids audio streaming.
// You MUST add your Google AI API key here for TTS to work.

const ttsApiKey = "AIzaSyCWnKnkH-P3kP1_ZRQTbVNr2VJZJ0jm15A"; // <--- PASTE YOUR GOOGLE AI API KEY HERE
const genTtsApiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key=${ttsApiKey}`;

/**
 * Calls the Gemini TTS API with exponential backoff.
 * @param {string} textToSpeak - The text to synthesize.
 * @param {string} [voice="Kore"] - The voice to use.
 * @param {number} [maxRetries=3] - Maximum number of retries.
 * @returns {Promise<object>} - The API response JSON with audio data.
 */
export async function callGeminiTTS(textToSpeak, voice = "Kore", maxRetries = 3) {
    if (!ttsApiKey) {
        console.error("TTS API Key is missing in js/api.js");
        throw new Error("TTS API Key is missing. Please add it to js/api.js.");
    }
    
    const payload = {
        contents: [{
            parts: [{ text: `Say in a professional, clear, and neutral tone: ${textToSpeak}` }]
        }],
        generationConfig: {
            responseModalities: ["AUDIO"],
            speechConfig: {
                voiceConfig: {
                    prebuiltVoiceConfig: { voiceName: voice }
                }
            }
        },
        model: "gemini-2.5-flash-preview-tts"
    };

    let attempt = 0;
    let delay = 1000;

    while (attempt < maxRetries) {
        try {
            const response = await fetch(genTtsApiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.statusText}`);
            }
            
            const result = await response.json();
            const part = result?.candidates?.[0]?.content?.parts?.[0];
            const audioData = part?.inlineData?.data;
            const mimeType = part?.inlineData?.mimeType;

            if (audioData && mimeType && mimeType.startsWith("audio/")) {
                return { audioData, mimeType }; // Success
            } else {
                throw new Error("Invalid audio response structure from API.");
            }
        } catch (error) {
            attempt++;
            if (attempt >= maxRetries) {
                console.error("Gemini TTS API call failed after max retries:", error);
                throw error;
            }
            console.warn(`Gemini TTS API call attempt ${attempt} failed. Retrying in ${delay}ms...`);
            await new Promise(resolve => setTimeout(resolve, delay));
            delay *= 2;
        }
    }
}
