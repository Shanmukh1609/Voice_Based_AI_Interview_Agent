import { startListening } from './speech.js';
import { showModal } from './ui.js';

/**
 * Decodes Base64 string to ArrayBuffer.
 * @param {string} base64 - The base64 encoded string.
 * @returns {ArrayBuffer}
 */
function base64ToArrayBuffer(base64) {
    const binaryString = window.atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
}

/**
 * Converts raw PCM16 audio data to a WAV file Blob.
 * @param {Int16Array} pcmData - The raw PCM data.
 * @param {number} sampleRate - The sample rate of the audio (e.g., 24000).
 * @returns {Blob} - A Blob object representing the WAV file.
 */
function pcmToWav(pcmData, sampleRate) {
    const numChannels = 1;
    const bitsPerSample = 16;
    const dataSize = pcmData.length * (bitsPerSample / 8);
    const blockAlign = numChannels * (bitsPerSample / 8);
    const byteRate = sampleRate * blockAlign;
    const buffer = new ArrayBuffer(44 + dataSize);
    const view = new DataView(buffer);

    // RIFF header
    view.setUint32(0, 0x52494646, false); // "RIFF"
    view.setUint32(4, 36 + dataSize, true);
    view.setUint32(8, 0x57415645, false); // "WAVE"
    // "fmt " sub-chunk
    view.setUint32(12, 0x666d7420, false); // "fmt "
    view.setUint32(16, 16, true); // Sub-chunk size
    view.setUint16(20, 1, true); // Audio format (1 = PCM)
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);
    // "data" sub-chunk
    view.setUint32(36, 0x64617461, false); // "data"
    view.setUint32(40, dataSize, true);

    // Write PCM data
    for (let i = 0; i < pcmData.length; i++) {
        view.setInt16(44 + i * 2, pcmData[i], true);
    }

    return new Blob([view], { type: 'audio/wav' });
}

/**
 * Plays the synthesized audio and triggers speech recognition on end.
 * @param {string} base64AudioData - The base64 audio data from the TTS API.
 * @param {string} mimeType - The mime type (contains sample rate).
 */
export function playAudioAndListen(base64AudioData, mimeType) {
    try {
        const sampleRateMatch = mimeType.match(/rate=(\d+)/);
        if (!sampleRateMatch) {
            throw new Error("Could not find sample rate in mimeType: " + mimeType);
        }
        const sampleRate = parseInt(sampleRateMatch[1], 10);
        
        const pcmData = base64ToArrayBuffer(base64AudioData);
        const pcm16 = new Int16Array(pcmData);
        const wavBlob = pcmToWav(pcm16, sampleRate);
        const audioUrl = URL.createObjectURL(wavBlob);
        
        const audio = new Audio(audioUrl);
        
        audio.onended = () => {
            URL.revokeObjectURL(audioUrl);
            // This is the key: Start listening AFTER the question is asked.
            startListening();
        };
        
        audio.onerror = (e) => {
            console.error("Error playing audio:", e);
            showModal("Audio Error", "Could not play the question. Please check your speakers.");
            // Even if audio fails, try to start listening
            startListening();
        };

        audio.play();

    } catch (error) {
        console.error("Error processing audio:", error);
        showModal("Audio Processing Error", `Failed to process audio: ${error.message}`);
        // Fallback: Start listening even if TTS fails
        startListening();
    }
}
