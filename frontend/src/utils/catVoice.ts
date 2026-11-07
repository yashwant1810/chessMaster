/**
 * Cat coach voice — calls backend Kokoro TTS, plays audio,
 * and drives mouth animation synced to actual audio playback.
 */

let audioCtx: AudioContext | null = null;
function getCtx(): AudioContext {
  if (!audioCtx) audioCtx = new AudioContext();
  return audioCtx;
}

/** Play a short "mrrp" meow */
function playMeow() {
  try {
    const ctx = getCtx();
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(900, now);
    osc.frequency.exponentialRampToValueAtTime(400, now + 0.15);
    osc.frequency.exponentialRampToValueAtTime(600, now + 0.25);
    gain.gain.setValueAtTime(0.08, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
    osc.connect(gain); gain.connect(ctx.destination);
    osc.start(now); osc.stop(now + 0.3);
  } catch { /* audio unavailable */ }
}

export interface CatSpeechCallbacks {
  onStart: () => void;
  onEnd: () => void;
  onMouthOpen?: () => void;
  onMouthClose?: () => void;
}

let currentAudio: HTMLAudioElement | null = null;
let mouthTimer: ReturnType<typeof setInterval> | null = null;

export function stopCatSpeech() {
  if (currentAudio) { currentAudio.pause(); currentAudio = null; }
  if (mouthTimer) { clearInterval(mouthTimer); mouthTimer = null; }
}

export async function catSpeak(text: string, callbacks: CatSpeechCallbacks): Promise<void> {
  stopCatSpeech();
  playMeow();

  try {
    // Call backend Kokoro TTS
    const resp = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice: "af_bella" }),
    });

    if (!resp.ok) {
      // Fallback to browser SpeechSynthesis
      return fallbackSpeak(text, callbacks);
    }

    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    currentAudio = audio;

    return new Promise<void>((resolve) => {
      audio.onplay = () => {
        callbacks.onStart();
        // Mouth animation: toggle every 300ms — natural talking pace
        let mouthOpen = false;
        mouthTimer = setInterval(() => {
          mouthOpen = !mouthOpen;
          if (mouthOpen) callbacks.onMouthOpen?.();
          else callbacks.onMouthClose?.();
        }, 400);
      };

      audio.onended = () => {
        stopMouth(callbacks);
        URL.revokeObjectURL(url);
        currentAudio = null;
        resolve();
      };

      audio.onerror = () => {
        stopMouth(callbacks);
        URL.revokeObjectURL(url);
        currentAudio = null;
        resolve();
      };

      audio.play().catch(() => {
        // Autoplay blocked — fall back to browser TTS
        URL.revokeObjectURL(url);
        currentAudio = null;
        fallbackSpeak(text, callbacks).then(resolve);
      });
    });
  } catch {
    // Network error — fall back to browser TTS
    return fallbackSpeak(text, callbacks);
  }
}

function stopMouth(callbacks: CatSpeechCallbacks) {
  if (mouthTimer) { clearInterval(mouthTimer); mouthTimer = null; }
  callbacks.onMouthClose?.();
  callbacks.onEnd();
}

/** Fallback: browser SpeechSynthesis if backend TTS unavailable */
function fallbackSpeak(text: string, callbacks: CatSpeechCallbacks): Promise<void> {
  return new Promise((resolve) => {
    if (!window.speechSynthesis) { resolve(); return; }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.pitch = 1.6;
    utterance.rate = 0.9;

    let mouthOpen = false;
    utterance.onstart = () => {
      callbacks.onStart();
      mouthTimer = setInterval(() => {
        mouthOpen = !mouthOpen;
        if (mouthOpen) callbacks.onMouthOpen?.();
        else callbacks.onMouthClose?.();
      }, 400);
    };
    utterance.onend = () => { stopMouth(callbacks); resolve(); };
    utterance.onerror = () => { stopMouth(callbacks); resolve(); };
    window.speechSynthesis.speak(utterance);
  });
}
