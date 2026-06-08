"""
J.A.Y. Speech-to-Text — Faster Whisper local STT with streaming
"""
import asyncio
import logging
import io
import wave
import numpy as np
from typing import Optional, AsyncGenerator
from app.core.config import settings

logger = logging.getLogger(__name__)


class SpeechToText:
    """
    Local speech recognition using faster-whisper.
    Falls back to online API if local model unavailable.
    """

    def __init__(self):
        self.model = None
        self.model_size = settings.STT_MODEL
        self.language = settings.STT_LANGUAGE
        self._loading = False

    def load_model(self):
        """Lazy-load Whisper model."""
        if self.model is not None:
            return
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Loading Whisper model: {self.model_size}")
            self.model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
                num_workers=2,
            )
            logger.info("Whisper model loaded")
        except Exception as e:
            logger.error(f"Failed to load Whisper: {e}")
            self.model = None

    async def transcribe_audio(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe audio bytes to text."""
        await asyncio.get_event_loop().run_in_executor(None, self.load_model)

        if self.model is None:
            return await self._transcribe_online(audio_data)

        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

            segments, info = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.transcribe(
                    audio_array,
                    language=self.language,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 500},
                ),
            )
            text = " ".join([seg.text.strip() for seg in segments])
            logger.debug(f"Transcribed: {text[:100]}")
            return text.strip()
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""

    async def transcribe_file(self, file_path: str) -> str:
        """Transcribe an audio file."""
        await asyncio.get_event_loop().run_in_executor(None, self.load_model)
        if self.model is None:
            return ""
        try:
            segments, _ = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.transcribe(file_path, language=self.language, vad_filter=True),
            )
            return " ".join([seg.text.strip() for seg in segments]).strip()
        except Exception as e:
            logger.error(f"File transcription error: {e}")
            return ""

    async def _transcribe_online(self, audio_data: bytes) -> str:
        """Fallback to OpenAI Whisper API."""
        try:
            from app.core.config import settings
            if not settings.OPENAI_API_KEY:
                return ""
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=("audio.wav", audio_data, "audio/wav"),
                language=self.language,
            )
            return response.text
        except Exception as e:
            logger.error(f"Online transcription failed: {e}")
            return ""


class VoiceActivityDetector:
    """
    Simple energy-based Voice Activity Detection.
    """
    def __init__(self, threshold: float = 0.01, min_duration_ms: int = 300):
        self.threshold = threshold
        self.min_duration_ms = min_duration_ms
        self.sample_rate = 16000

    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """Detect if audio chunk contains speech."""
        energy = np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2)) / 32768.0
        return energy > self.threshold

    def detect_speech_segments(
        self,
        audio: np.ndarray,
        frame_ms: int = 30,
    ) -> list:
        """Find speech segments in audio."""
        frame_size = int(self.sample_rate * frame_ms / 1000)
        segments = []
        in_speech = False
        start = 0

        for i in range(0, len(audio), frame_size):
            frame = audio[i:i + frame_size]
            if self.is_speech(frame):
                if not in_speech:
                    start = i
                    in_speech = True
            else:
                if in_speech:
                    duration_ms = (i - start) / self.sample_rate * 1000
                    if duration_ms >= self.min_duration_ms:
                        segments.append((start, i))
                    in_speech = False

        return segments


stt = SpeechToText()
vad = VoiceActivityDetector()
