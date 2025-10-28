import {
    setupScreen, reportScreen, startInterviewBtn, restartBtn,
    resumeFile, resumeText,
    questionText, answerText, reportStatus,
    showModal, updateStatus, switchScreen
} from './ui.js';

import {
    uploadResume, getQuestions, evaluateInterview, sendEmail, callGeminiTTS
} from './api.js';

import { playAudioAndListen } from './audio.js';
import { setupSpeechRecognition } from './speech.js';

// --- State Variables ---
let questions = [];
let transcript = [];
let currentQuestionIndex = 0;
let finalEvaluation = ""; // Store the final report text

// --- Core Application Flow ---

/**
 * 1. Entry point: User clicks "Start Interview"
 */
async function handleStartInterview() {
    startInterviewBtn.disabled = true;
    startInterviewBtn.textContent = 'Parsing Resume...';

    // === 1. VALIDATE INPUTS ===
    const file = resumeFile.files[0];
    
    // Removed validation for jobDescription, companyFactsText, and hrEmailAddress

    if (!file) {
        showModal("Missing Information", "Please upload a resume PDF.");
        startInterviewBtn.disabled = false;
        startInterviewBtn.textContent = 'Start Interview';
        return;
    }
    
    // === 2. SETUP SPEECH RECOGNITION ===
    if (!setupSpeechRecognition({ onAnswer: handleSpeechEnd })) {
        startInterviewBtn.disabled = false;
        startInterviewBtn.textContent = 'Start Interview';
        return; // STT setup failed
    }

    try {
        // === 3. UPLOAD & PARSE RESUME ===
        const uploadResponse = await uploadResume(file);
        resumeText.value = uploadResponse.resume_text; // Store parsed text
        
        // === 4. GENERATE QUESTIONS ===
        startInterviewBtn.textContent = 'Generating Questions...';
        // Call getQuestions with only the resume text
        const questionsResponse = await getQuestions(
            resumeText.value
        );
        
        questions = questionsResponse.questions;
        if (questions.length === 0) {
            throw new Error("Backend did not return any questions.");
        }
        
        // === 5. START INTERVIEW Q&A LOOP ===
        switchScreen('interview');
        askQuestion(0); // Start with the first question

    } catch (error) {
        console.error("Failed to start interview:", error);
        showModal("Error", `Failed to start interview: ${error.message}`);
        startInterviewBtn.disabled = false;
        startInterviewBtn.textContent = 'Start Interview';
    }
}

/**
 * 3. Ask a single question (TTS) and prepare to listen.
 * @param {number} index - The index of the question to ask.
 */
async function askQuestion(index) {
    if (index >= questions.length) {
        finishInterview();
        return;
    }

    const question = questions[index];
    questionText.textContent = question;
    answerText.textContent = ''; // Clear previous answer
    updateStatus(`Asking question ${index + 1} of ${questions.length}...`);

    try {
        // Call TTS API (from frontend js/api.js)
        const { audioData, mimeType } = await callGeminiTTS(question);
        // The playAudio function will call startListening() onended
        playAudioAndListen(audioData, mimeType);
    } catch (error) {
        console.error("TTS Error:", error);
        showModal("TTS Error", `Could not generate audio for the question: ${error.message}. I will start listening instead.`);
        // Fallback: If TTS fails, just start listening
        // Note: startListening() is now called by playAudioAndListen, even on error.
    }
}

/**
 * 4. Callback for when speech recognition provides a final answer.
 * @param {string} answer - The final answer from the speech service.
 */
function handleSpeechEnd(answer) {
    // Save to transcript
    transcript.push({
        question: questions[currentQuestionIndex],
        answer: answer
    });

    // Move to the next question or finish
    currentQuestionIndex++;
    if (currentQuestionIndex < questions.length) {
        askQuestion(currentQuestionIndex);
    } else {
        finishInterview();
    }
}


/**
 * 5. All questions are done, now evaluate the interview.
 */
async function finishInterview() {
    updateStatus("Interview complete! Evaluating your answers...");
    switchScreen('report'); // Show the report screen
    reportStatus.textContent = "Evaluating performance and sending report to the hiring team...";

    try {
        // === 6. GET EVALUATION ===
        const evalResponse = await evaluateInterview(transcript);
        finalEvaluation = evalResponse.evaluation; // Store for email
        
        // --- Report rendering is REMOVED ---
        // We no longer display the report content in the UI.
        
        // === 7. SEND EMAIL ===
        reportStatus.textContent = `Evaluation complete! Sending report to the hiring team...`;
        
        // Call sendEmail without hr_email argument
        await sendEmail(
            resumeText.value,
            finalEvaluation
        );
        
        // Update status to final confirmation
        reportStatus.textContent = `Your evaluation has been sent to the hiring team. Thank you!`;

    } catch (error) {
        console.error("Failed to generate or send report:", error);
        // Display a more user-friendly error on the report screen
        reportStatus.textContent = "An error occurred while sending your report. Please contact the administrator.";
    }
}

// --- Initial Event Listeners ---
startInterviewBtn.addEventListener('click', handleStartInterview);
restartBtn.addEventListener('click', () => {
    // Reset everything
    switchScreen('setup');
    questions = [];
    transcript = [];
    currentQuestionIndex = 0;
    finalEvaluation = "";
    
    // Clear form fields
    resumeFile.value = '';
    resumeText.value = '';
    
    reportStatus.textContent = "Generating your evaluation...";
});
