import {
    setupScreen, reportScreen, startInterviewBtn, restartBtn,
    resumeFile, resumeText, jobDesc, companyFacts, hrEmail,
    questionText, answerText, reportContent, reportStatus,
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
    const jobDescription = jobDesc.value.trim();
    const companyFactsText = companyFacts.value.trim();
    const hrEmailAddress = hrEmail.value.trim();

    if (!file) {
        showModal("Missing Information", "Please upload a resume PDF.");
        startInterviewBtn.disabled = false;
        startInterviewBtn.textContent = 'Start Interview';
        return;
    }
    if (!jobDescription) {
        showModal("Missing Information", "Please provide a job description.");
        startInterviewBtn.disabled = false;
        startInterviewBtn.textContent = 'Start Interview';
        return;
    }
    if (!hrEmailAddress) {
        showModal("Missing Information", "Please provide an HR email to send the report.");
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
        const questionsResponse = await getQuestions(
            resumeText.value,
            jobDescription,
            companyFactsText
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
    switchScreen('report'); // Show the report screen (with loading message)
    reportStatus.textContent = "Evaluating performance...";

    try {
        // === 6. GET EVALUATION ===
        const evalResponse = await evaluateInterview(transcript);
        finalEvaluation = evalResponse.evaluation; // Store for email
        
        // Render the report
        let htmlReport = finalEvaluation
            .replace(/\*\*(.*?)\*\*/g, '<strong class="text-gray-900">$1</strong>')
            .replace(/^- (.*)/gm, '<li class="ml-4">$1</li>')
            .replace(/(\n<li>)/g, '<li>')
            .replace(/<\/li>\n/g, '</li>');
        
        htmlReport = htmlReport.replace(/(<li>.*<\/li>)/gs, '<ul class="list-disc list-outside mb-4">$1</ul>');
        htmlReport = htmlReport.split('\n').map(p => {
            if (p.startsWith('<ul') || p.startsWith('<li') || p.startsWith('<strong')) return p;
            return `<p class="mb-4">${p}</p>`;
        }).join('');

        reportContent.innerHTML = htmlReport;
        
        // === 7. SEND EMAIL ===
        reportStatus.textContent = `Evaluation complete! Sending report to ${hrEmail.value}...`;
        await sendEmail(
            hrEmail.value,
            resumeText.value,
            finalEvaluation
        );
        reportStatus.textContent = `Evaluation complete! Report sent to ${hrEmail.value}.`;

    } catch (error) {
        console.error("Failed to generate or send report:", error);
        reportContent.innerHTML = `<p class="text-red-500">Sorry, an error occurred while generating the report: ${error.message}</p>`;
        reportStatus.textContent = "An error occurred during the final report step.";
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
    jobDesc.value = '';
    companyFacts.value = '';
    hrEmail.value = '';
    
    // Reset report screen
    reportContent.innerHTML = '<p>Generating report...</p>';
    reportStatus.textContent = "Here is the AI-generated evaluation. Sending report to HR...";
});