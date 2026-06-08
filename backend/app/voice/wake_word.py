"""
J.A.Y. Wake Word Detection — "Hey J.A.Y.", "Wake up J.A.Y.", "J.A.Y."
"""
import asyncio
import logging
import threading
import queue
from typing import Callable, Optional, List
from app.core.config import settings
from app.core.events import event_bus, Events

logger = logging.getLogger(__name__)


class WakeWordDetector:
    """
    Wake word detection supporting two modes:
    1. Porcupine (high accuracy, requires API key)
    2. Simple energy + keyword matching (fallback, no API key needed)
    """

    def __init__(self):
        self.wake_words = settings.WAKE_WORDS
        self.is_listening = False
        self._audio_queue: queue.Queue = queue.Queue()
        self._callback: Optional[Callable] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def set_callback(self, callback: Callable):
        self._callback = callback

    async def start(self):
        """Start passive wake word listening."""
        if self.is_listening:
            return
        self.is_listening = True
        self._stop_event.clear()

        # Try Porcupine first
        if settings.PVPORCUPINE_ACCESS_KEY:
            success = await self._start_porcupine()
            if success:
                logger.info("Wake word detection: Porcupine active")
                return

        # Fallback: Whisper-based keyword detection
        await self._start_whisper_fallback()
        logger.info("Wake word detection: Whisper fallback active")

    async def stop(self):
        """Stop wake word detection."""
        self.is_listening = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Wake word detection stopped")

    async def _start_porcupine(self) -> bool:
        """Start Porcupine wake word detection."""
        try:
            import pvporcupine
            import pyaudio

            # Use built-in "hey jarvis" as closest, or custom keyword files
            porcupine = pvporcupine.create(
                access_key=settings.PVPORCUPINE_ACCESS_KEY,
                keywords=["hey siri"],  # Fallback built-in; custom files needed for "hey jay"
            )

            audio = pyaudio.PyAudio()
            stream = audio.open(
                rate=porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=porcupine.frame_length,
            )

            def _listen():
                import struct
                while not self._stop_event.is_set():
                    try:
                        pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
                        pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)
                        result = porcupine.process(pcm_unpacked)
                        if result >= 0:
                            asyncio.run_coroutine_threadsafe(
                                self._on_wake_word_detected(), asyncio.get_event_loop()
                            )
                    except Exception as e:
                        logger.error(f"Porcupine listen error: {e}")
                        break

                stream.close()
                audio.terminate()
                porcupine.delete()

            self._thread = threading.Thread(target=_listen, daemon=True)
            self._thread.start()
            return True

        except Exception as e:
            logger.warning(f"Porcupine not available: {e}")
            return False

    async def _start_whisper_fallback(self):
        """Fallback: use Whisper periodically to detect wake words."""
        import numpy as np

        def _listen():
            try:
                import sounddevice as sd
                from app.voice.stt import stt
                import asyncio

                SAMPLE_RATE = 16000
                CHUNK_DURATION = 2.0  # 2-second chunks
                chunk_size = int(SAMPLE_RATE * CHUNK_DURATION)

                logger.info("Whisper wake word fallback listening...")

                while not self._stop_event.is_set():
                    audio_chunk = sd.rec(
                        chunk_size,
                        samplerate=SAMPLE_RATE,
                        channels=1,
                        dtype="int16",
                        blocking=True,
                    )
                    audio_bytes = audio_chunk.tobytes()

                    # Run async transcription in this thread
                    loop = asyncio.new_event_loop()
                    text = loop.run_until_complete(stt.transcribe_audio(audio_bytes))
                    loop.close()

                    if text:
                        text_lower = text.lower().strip()
                        for ww in settings.WAKE_WORDS:
                            if ww.lower() in text_lower:
                                asyncio.run_coroutine_threadsafe(
                                    self._on_wake_word_detected(),
                                    asyncio.get_event_loop(),
                                )
                                break

            except Exception as e:
                logger.error(f"Wake word fallback error: {e}")
                self.is_listening = False

        self._thread = threading.Thread(target=_listen, daemon=True)
        self._thread.start()

    async def _on_wake_word_detected(self):
        """Called when wake word is detected."""
        logger.info("Wake word detected!")
        await event_bus.publish(Events.WAKE_WORD_DETECTED, {"detected": True})
        if self._callback:
            await self._callback()


class VoicePipeline:
    """
    Full voice pipeline: wake word → STT → LLM → TTS
    """

    def __init__(self):
        self.detector = WakeWordDetector()
        self.is_active = False
        self._active_conversation = False

    async def start(self, on_transcript: Callable = None):
        """Start the voice pipeline."""
        self.detector.set_callback(lambda: self._handle_wake_word(on_transcript))
        await self.detector.start()
        logger.info("Voice pipeline started")

    async def stop(self):
        await self.detector.stop()
        logger.info("Voice pipeline stopped")

    async def _handle_wake_word(self, on_transcript: Callable = None):
        """After wake word: record speech and transcribe."""
        from app.voice.stt import stt
        from app.voice.tts import tts
        import sounddevice as sd

        await event_bus.publish(Events.SPEECH_STARTED, {})

        # Play acknowledgment tone
        try:
            audio = await tts.speak("Yes?")
            # Play audio
        except Exception:
            pass

        # Record speech
        SAMPLE_RATE = 16000
        MAX_DURATION = 10  # seconds
        try:
            audio_data = sd.rec(
                int(MAX_DURATION * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
            )
            sd.wait()
            audio_bytes = audio_data.tobytes()
            text = await stt.transcribe_audio(audio_bytes)

            await event_bus.publish(Events.SPEECH_ENDED, {})
            await event_bus.publish(Events.TRANSCRIPT_READY, {"text": text})

            if text and on_transcript:
                await on_transcript(text)

        except Exception as e:
            logger.error(f"Voice recording error: {e}")

    async def speak(self, text: str) -> bytes:
        """Speak text and return audio bytes."""
        from app.voice.tts import tts
        await event_bus.publish(Events.TTS_STARTED, {"text": text[:50]})
        audio = await tts.speak(text)
        await event_bus.publish(Events.TTS_COMPLETE, {})
        return audio


voice_pipeline = VoicePipeline()
