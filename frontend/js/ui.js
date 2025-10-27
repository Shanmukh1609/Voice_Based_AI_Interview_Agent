// --- DOM Elements ---
export const setupScreen = document.getElementById('setup-screen');
export const interviewScreen = document.getElementById('interview-screen');
export const reportScreen = document.getElementById('report-screen');

export const startInterviewBtn = document.getElementById('start-interview-btn');
export const restartBtn = document.getElementById('restart-btn');

// Setup Screen Inputs
export const resumeFile = document.getElementById('resume-file');
export const resumeText = document.getElementById('resume-text'); // Hidden input
export const jobDesc = document.getElementById('job-desc');
export const companyFacts = document.getElementById('company-facts');
export const hrEmail = document.getElementById('hr-email');

// Interview Screen Elements
export const statusMessage = document.getElementById('status-message');
export const listeningIndicator = document.getElementById('listening-indicator');
export const questionText = document.getElementById('question-text');
export const answerText = document.getElementById('answer-text');

// Report Screen Elements
export const reportContent = document.getElementById('report-content');
export const reportStatus = document.getElementById('report-status');

// Modal Elements
export const messageModal = document.getElementById('message-modal');
const modalTitle = document.getElementById('modal-title');
const modalMessage = document.getElementById('modal-message');
const modalCloseBtn = document.getElementById('modal-close-btn');

// --- Event Listeners ---
modalCloseBtn.addEventListener('click', () => {
    messageModal.classList.add('hidden');
});

// --- Utility Functions ---

/**
 * Shows a modal message to the user.
 * @param {string} title - The title for the modal.
 * @param {string} message - The message to display.
 */
export function showModal(title, message) {
    modalTitle.textContent = title;
    modalMessage.textContent = message;
    messageModal.classList.remove('hidden');
}

/**
 * Updates the main status message on the interview screen.
 * @param {string} text - The message to display.
 * @param {boolean} [showListening=false] - Whether to show the listening animation.
 */
export function updateStatus(text, showListening = false) {
    statusMessage.textContent = text;
    if (showListening) {
        listeningIndicator.classList.remove('hidden');
    } else {
        listeningIndicator.classList.add('hidden');
    }
}

/**
 * Switches the visible screen.
 * @param {'setup' | 'interview' | 'report'} screenName - The screen to show.
 */
export function switchScreen(screenName) {
    setupScreen.classList.add('hidden');
    interviewScreen.classList.add('hidden');
    reportScreen.classList.add('hidden');

    if (screenName === 'setup') {
        setupScreen.classList.remove('hidden');
    } else if (screenName === 'interview') {
        interviewScreen.classList.remove('hidden');
    } else if (screenName === 'report') {
        reportScreen.classList.remove('hidden');
    }
}