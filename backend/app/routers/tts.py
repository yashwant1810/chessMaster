"""TTS endpoint for cat coach voice."""

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

from app.services.tts_service import generate_cat_speech

router = APIRouter(prefix="/api/tts", tags=["tts"])


class TTSRequest(BaseModel):
    text: str
    voice: str = "af_bella"


@router.post("")
async def text_to_speech(body: TTSRequest) -> Response:
    """Generate cat-like TTS audio from text."""
    wav_bytes = generate_cat_speech(body.text, voice=body.voice)
    return Response(content=wav_bytes, media_type="audio/wav")
