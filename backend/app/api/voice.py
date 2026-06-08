"""
J.A.Y. Voice API — STT, TTS, wake word control
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import Optional
import logging
import io

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/voice", tags=["voice"])


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    stream: bool = False


class VoiceStatusResponse(BaseModel):
    wake_word_active: bool
    pipeline_active: bool
    current_voice: str


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe uploaded audio to text."""
    from app.voice.stt import stt
    try:
        audio_data = await file.read()
        text = await stt.transcribe_audio(audio_data)
        return {"text": text, "language": stt.language}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speak")
async def text_to_speech(request: TTSRequest):
    """Convert text to speech audio (MP3)."""
    from app.voice.tts import tts
    try:
        if request.voice:
            tts.voice = request.voice

        if request.stream:
            async def audio_stream():
                async for chunk in tts.stream_speak(request.text):
                    yield chunk
            return StreamingResponse(audio_stream(), media_type="audio/mpeg")
        else:
            audio = await tts.speak(request.text)
            return Response(content=audio, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wake-word/start")
async def start_wake_word():
    """Start wake word detection."""
    from app.voice.wake_word import voice_pipeline
    try:
        await voice_pipeline.detector.start()
        return {"status": "started", "wake_words": ["hey jay", "wake up jay", "j.a.y."]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wake-word/stop")
async def stop_wake_word():
    """Stop wake word detection."""
    from app.voice.wake_word import voice_pipeline
    try:
        await voice_pipeline.detector.stop()
        return {"status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voices")
async def list_voices():
    """List available TTS voices."""
    from app.voice.tts import tts
    voices = await tts.list_voices()
    return {"voices": voices}


@router.get("/status")
async def voice_status():
    """Get voice system status."""
    from app.voice.wake_word import voice_pipeline
    from app.voice.tts import tts
    return VoiceStatusResponse(
        wake_word_active=voice_pipeline.detector.is_listening,
        pipeline_active=voice_pipeline.is_active,
        current_voice=tts.voice,
    )
