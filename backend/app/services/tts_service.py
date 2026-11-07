"""Cat TTS service using Kokoro-ONNX with pitch shift."""

import io
import os
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

MODEL_PATH = os.environ.get("KOKORO_MODEL_PATH", "kokoro-v1.0.onnx")
VOICES_PATH = os.environ.get("KOKORO_VOICES_PATH", "voices-v1.0.bin")

_kokoro: Kokoro | None = None


def _get_kokoro() -> Kokoro:
    global _kokoro
    if _kokoro is None:
        _kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
    return _kokoro


def pitch_shift_simple(audio: np.ndarray, sr: int, semitones: float = 4.0) -> tuple[np.ndarray, int]:
    """Pitch shift by resampling — raise pitch by speeding up then resampling back.
    
    No librosa needed — pure numpy approach.
    """
    factor = 2.0 ** (semitones / 12.0)
    # Resample: take every factor-th sample (speeds up = higher pitch)
    indices = np.arange(0, len(audio), factor)
    indices = indices[indices < len(audio)].astype(int)
    shifted = audio[indices]
    return shifted, sr


def generate_cat_speech(text: str, voice: str = "af_bella") -> bytes:
    """Generate cat-like speech audio as WAV bytes."""
    kokoro = _get_kokoro()
    samples, sr = kokoro.create(text, voice=voice, speed=0.95)
    
    # Pitch shift up 3 semitones for cat-like quality
    samples, sr = pitch_shift_simple(samples, sr, semitones=3.0)
    
    # Write to WAV bytes
    buf = io.BytesIO()
    sf.write(buf, samples, sr, format="WAV")
    buf.seek(0)
    return buf.read()
