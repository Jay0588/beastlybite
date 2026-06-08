"""
J.A.Y. Text-to-Speech — Edge TTS (human-like, streaming) with fallback
"""
import asyncio
import logging
import io
from typing import AsyncGenerator, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class TextToSpeech:
    """
    High-quality TTS using Microsoft Edge TTS (free, local, human-like).
    Falls back to pyttsx3 for offline fallback.
    """

    def __init__(self):
        self.voice = settings.TTS_VOICE
        self.rate = settings.TTS_RATE
        self.pitch = settings.TTS_PITCH

    async def speak(self, text: str) -> bytes:
        """Convert text to audio bytes (MP3)."""
        text = self._clean_text(text)
        if not text:
            return b""

        try:
            import edge_tts
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch,
            )
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data
        except Exception as e:
            logger.error(f"Edge TTS failed: {e}")
            return await self._fallback_tts(text)

    async def stream_speak(self, text: str) -> AsyncGenerator[bytes, None]:
        """Stream TTS audio chunks."""
        text = self._clean_text(text)
        if not text:
            return

        try:
            import edge_tts
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch,
            )
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        except Exception as e:
            logger.error(f"Edge TTS stream failed: {e}")
            # Fallback: yield full audio at once
            audio = await self._fallback_tts(text)
            if audio:
                yield audio

    async def speak_and_play(self, text: str):
        """Speak text through system audio."""
        audio = await self.speak(text)
        if audio:
            await self._play_audio(audio)

    async def _play_audio(self, audio_data: bytes):
        """Play audio through system speakers."""
        try:
            import sounddevice as sd
            import soundfile as sf
            buf = io.BytesIO(audio_data)
            data, samplerate = sf.read(buf)
            sd.play(data, samplerate)
            sd.wait()
        except Exception as e:
            logger.error(f"Audio playback failed: {e}")

    async def _fallback_tts(self, text: str) -> bytes:
        """Fallback TTS using pyttsx3."""
        try:
            import pyttsx3
            import tempfile
            engine = pyttsx3.init()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp = f.name
            engine.save_to_file(text, tmp)
            engine.runAndWait()
            with open(tmp, "rb") as f:
                data = f.read()
            import os
            os.unlink(tmp)
            return data
        except Exception as e:
            logger.error(f"Fallback TTS failed: {e}")
            return b""

    def _clean_text(self, text: str) -> str:
        """Clean text for TTS — remove markdown, code blocks, etc."""
        import re
        # Remove markdown
        text = re.sub(r'```[^`]*```', 'code block', text, flags=re.DOTALL)
        text = re.sub(r'`[^`]+`', '', text)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'#{1,6}\s+', '', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    async def list_voices(self) -> list:
        """List available Edge TTS voices."""
        try:
            import edge_tts
            voices = await edge_tts.list_voices()
            return [{"name": v["Name"], "locale": v["Locale"], "gender": v["Gender"]} for v in voices]
        except Exception:
            return []


tts = TextToSpeech()
