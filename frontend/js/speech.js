import { showModal, updateStatus, answerText } from './ui.js';

let speechRecognition;
let isListening = false;
let currentAnswer = '';
let callbacks = {}; // To store onAnswer and onNoSpeech
let silenceTimer; // <-- MODIFIED: Variable to hold our silence timer


const PAUSE_DURATION_MS = 6000;

/**
 * Initializes the Speech Recognition API.
 * @param {object} cbs - Callbacks for speech events.
 * @param {function} cbs.onAnswer - Called with the final answer.
 */
export function setupSpeechRecognition(cbs) {
    callbacks = cbs; // Store callbacks
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        showModal("Browser Not Supported", "Your browser does not support the Speech Recognition API. Please try Chrome or Edge.");
        return false;
    }

    speechRecognition = new SpeechRecognition();
    
    // --- MODIFIED ---
    // We set to 'true' so we can control the silence, not the browser.
    speechRecognition.continuous = true; 
    
    speechRecognition.interimResults = true; // Show results as they come in
    speechRecognition.lang = 'en-US';

    // Event: When speech is first detected
    speechRecognition.onaudiostart = () => {
        isListening = true;
        currentAnswer = ''; // Clear previous interim answer
        updateStatus("Listening...", true);
    };

    // Event: As results come in
    speechRecognition.onresult = (event) => {
        
        // --- MODIFIED ---
        // Reset the silence timer every time new speech is detected
        clearTimeout(silenceTimer);
        silenceTimer = setTimeout(() => {
            if (isListening) {
                console.log(`Silence detected. Stopping after ${PAUSE_DURATION_MS}ms.`);
                speechRecognition.stop(); // This will trigger the 'onend' event
            }
        }, PAUSE_DURATION_MS);
        // --- END OF MODIFICATION ---

        
        let interimTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
                currentAnswer += event.results[i][0].transcript + ' ';
            } else {
                interimTranscript += event.results[i][0].transcript;
            }
        }
        answerText.textContent = currentAnswer + interimTranscript; // Show final + interim
    };

    // Event: When speech ends (e.g., silence)
    speechRecognition.onend = () => {
        
        // --- MODIFIED ---
        // Always clear the timer when recognition ends
        clearTimeout(silenceTimer);
        
        isListening = false;
        updateStatus("Processing your answer...", false);
        
        let finalAnswer = currentAnswer.trim();
        if (finalAnswer.length === 0) {
            finalAnswer = "[No answer provided]";
        }
        
        // Finalize the answer
        answerText.textContent = finalAnswer;
        
        // Use the callback
        if (callbacks.onAnswer) {
            callbacks.onAnswer(finalAnswer);
        }
    };

    // Event: On error
    speechRecognition.onerror = (event) => {
        
        // --- MODIFIED ---
        clearTimeout(silenceTimer); // Also clear timer on error
        
        isListening = false;
        updateStatus("Ready", false);
        let errorMsg = event.error;

        // --- MODIFIED ---
        // With continuous=true, 'no-speech' is less common.
        // We now rely on our timer to handle silence.
        // But if it does happen, we treat it as an empty answer.
        if (event.error === 'no-speech') {
            const finalAnswer = "[No answer provided]";
            answerText.textContent = finalAnswer;
            if (callbacks.onAnswer) {
                callbacks.onAnswer(finalAnswer);
            }
        } else if (event.error === 'not-allowed') {
            showModal("Permission Denied", "You must allow microphone access to use this app. Please refresh and grant permission.");
        } else {
            console.error("Speech recognition error:", event.error);
            showModal("Speech Error", `An error occurred: ${errorMsg}.`);
        }
    };
    
    return true;
}

/**
 * Starts the STT listening process.
 */
export function startListening() {
    if (speechRecognition && !isListening) {
        try {
            answerText.textContent = ''; // Clear last answer
            currentAnswer = ''; // Clear answer buffer
            speechRecognition.start();
            
            // --- MODIFIED ---
            // Start the silence timer immediately.
            // If the user says nothing, this will fire and stop the mic.
            // If they speak, 'onresult' will clear this timer and set a new one.
            clearTimeout(silenceTimer); // Clear any old timers
            silenceTimer = setTimeout(() => {
                if (isListening) {
                    console.log("Initial silence. Stopping.");
                    speechRecognition.stop();
                }
            }, PAUSE_DURATION_MS);
            // --- END OF MODIFICATION ---
            
        } catch (error) {
            // This can happen if start() is called too soon after stop()
            console.warn("Speech recognition start error:", error);
            // Try again after a short delay
            setTimeout(() => {
                try {
                    speechRecognition.start();
                } catch (e) {
                    console.error("Speech recognition failed to restart:", e);
                    showModal("Mic Error", "Could not start the microphone. Please check permissions and try again.");
                }
            }, 500);
        }
    }
}