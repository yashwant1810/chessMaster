/**
 * Chess move sound effects using Web Audio API.
 * No external sound files needed — generates short tones programmatically.
 */

let audioCtx: AudioContext | null = null;

function getCtx(): AudioContext {
  if (!audioCtx) audioCtx = new AudioContext();
  return audioCtx;
}

function playTone(freq: number, duration: number, type: OscillatorType = "sine", volume = 0.15) {
  try {
    const ctx = getCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(volume, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + duration);
  } catch {
    // Audio not available — silently skip
  }
}

/** Normal piece move — short wooden tap */
export function playMoveSound() {
  playTone(800, 0.08, "square", 0.1);
  setTimeout(() => playTone(400, 0.06, "sine", 0.08), 15);
}

/** Capture — sharper, two-part sound */
export function playCaptureSound() {
  playTone(600, 0.06, "square", 0.12);
  setTimeout(() => playTone(300, 0.1, "triangle", 0.15), 30);
}

/** Check — higher pitched alert */
export function playCheckSound() {
  playTone(1200, 0.1, "sine", 0.12);
  setTimeout(() => playTone(900, 0.12, "sine", 0.1), 60);
}

/** Game over (checkmate/stalemate) — descending tone */
export function playGameEndSound() {
  playTone(800, 0.15, "sine", 0.12);
  setTimeout(() => playTone(600, 0.15, "sine", 0.1), 100);
  setTimeout(() => playTone(400, 0.25, "sine", 0.08), 200);
}

/**
 * Pick the right sound based on the move's SAN notation.
 */
export function playSoundForMove(san: string) {
  if (!san) return;
  if (san.includes("#")) {
    playGameEndSound();
  } else if (san.includes("+")) {
    playCheckSound();
  } else if (san.includes("x")) {
    playCaptureSound();
  } else {
    playMoveSound();
  }
}
