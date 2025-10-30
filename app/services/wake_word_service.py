"""
Wake word detection service for ARIA activation.
"""

import logging
import asyncio
import tempfile
import os
from typing import Optional, Dict, Any, List
import re
import time
from datetime import datetime

from app.core.config import settings

# Try to import PyAudio for audio recording
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

# Try to import Whisper
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

logger = logging.getLogger(__name__)


class WakeWordService:
    """Service for wake word detection and activation."""
    
    def __init__(self):
        self.enabled = True
        self.wake_words = ["aria", "hey aria", "ok aria", "hello aria"]
        self.listening = False
        self.whisper_model = None
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required dependencies are available."""
        try:
            if not PYAUDIO_AVAILABLE:
                logger.warning("PyAudio not available - wake word detection may not work")
                self.enabled = False
                return
            
            if not WHISPER_AVAILABLE:
                logger.warning("Whisper not available - wake word detection may not work")
                self.enabled = False
                return
            
            logger.info("Wake word service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize wake word service: {e}")
            self.enabled = False
    
    async def load_whisper_model(self):
        """Load Whisper model for wake word detection."""
        if not WHISPER_AVAILABLE or self.whisper_model:
            return
        
        try:
            import concurrent.futures
            
            def load_model():
                try:
                    # Use tiny model for fast wake word detection
                    model = whisper.load_model("tiny")
                    logger.info("Loaded Whisper tiny model for wake word detection")
                    return model
                except Exception as e:
                    logger.debug(f"Failed to load Whisper model: {e}")
                    return None
            
            # Load model in thread pool
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                self.whisper_model = await loop.run_in_executor(executor, load_model)
                
            if self.whisper_model:
                logger.info("Wake word detection ready")
            else:
                logger.warning("Could not load Whisper model for wake word detection")
                
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
    
    async def start_continuous_listening(self):
        """Start continuous listening for wake words in background."""
        if not self.enabled:
            logger.warning("Wake word service is not enabled")
            return
        
        if self.listening:
            logger.info("Wake word listening is already active")
            return
        
        # Load Whisper model if not already loaded
        if not self.whisper_model:
            await self.load_whisper_model()
        
        if not self.whisper_model:
            logger.error("Cannot start wake word listening without Whisper model")
            return
        
        self.listening = True
        logger.info("Starting continuous wake word listening...")
        
        # Start background listening task
        asyncio.create_task(self._continuous_listen_loop())
    
    async def stop_continuous_listening(self):
        """Stop continuous listening for wake words."""
        self.listening = False
        logger.info("Stopped continuous wake word listening")
    
    async def _continuous_listen_loop(self):
        """Continuous listening loop for wake words."""
        while self.listening:
            try:
                # Listen for short audio chunks
                audio_file = await self._record_audio_chunk(duration=3)
                
                if audio_file:
                    # Check for wake word
                    wake_word_detected = await self._detect_wake_word(audio_file)
                    
                    # Clean up audio file
                    if os.path.exists(audio_file):
                        os.unlink(audio_file)
                    
                    if wake_word_detected:
                        logger.info("Wake word detected! Activating ARIA...")
                        await self._handle_wake_word_activation()
                
                # Small delay to prevent excessive CPU usage
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in wake word listening loop: {e}")
                await asyncio.sleep(2)  # Longer delay on error
    
    async def _record_audio_chunk(self, duration: int = 3) -> Optional[str]:
        """Record a short audio chunk for wake word detection."""
        if not PYAUDIO_AVAILABLE:
            return None
        
        try:
            import concurrent.futures
            import wave
            
            def record_audio():
                # Audio recording parameters optimized for speech
                CHUNK = 1024
                FORMAT = pyaudio.paInt16
                CHANNELS = 1
                RATE = 16000
                
                # Create temporary WAV file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    audio_path = temp_file.name
                
                # Initialize PyAudio
                p = pyaudio.PyAudio()
                
                try:
                    # Open stream
                    stream = p.open(format=FORMAT,
                                  channels=CHANNELS,
                                  rate=RATE,
                                  input=True,
                                  frames_per_buffer=CHUNK)
                    
                    frames = []
                    for i in range(0, int(RATE / CHUNK * duration)):
                        data = stream.read(CHUNK, exception_on_overflow=False)
                        frames.append(data)
                    
                    # Stop and close the stream
                    stream.stop_stream()
                    stream.close()
                    
                    # Save the recorded data as a WAV file
                    wf = wave.open(audio_path, 'wb')
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(p.get_sample_size(FORMAT))
                    wf.setframerate(RATE)
                    wf.writeframes(b''.join(frames))
                    wf.close()
                    
                    return audio_path
                    
                finally:
                    p.terminate()
            
            # Run recording in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                audio_path = await loop.run_in_executor(executor, record_audio)
                
            return audio_path if audio_path and os.path.exists(audio_path) else None
            
        except Exception as e:
            logger.debug(f"Error recording audio chunk: {e}")
            return None
    
    async def _detect_wake_word(self, audio_file: str) -> bool:
        """Detect if audio contains a wake word."""
        if not self.whisper_model:
            return False
        
        try:
            import concurrent.futures
            
            def transcribe_audio():
                try:
                    # Transcribe the audio
                    result = self.whisper_model.transcribe(audio_file, language="en")
                    text = result["text"].strip().lower()
                    return text
                except Exception as e:
                    logger.debug(f"Transcription error: {e}")
                    return ""
            
            # Run transcription in thread pool
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                transcribed_text = await loop.run_in_executor(executor, transcribe_audio)
            
            if not transcribed_text:
                return False
            
            # Check if any wake word is present
            for wake_word in self.wake_words:
                if wake_word in transcribed_text:
                    logger.info(f"Wake word '{wake_word}' detected in: '{transcribed_text}'")
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Wake word detection error: {e}")
            return False
    
    async def _handle_wake_word_activation(self):
        """Handle wake word activation - start conversation."""
        try:
            # Import here to avoid circular imports
            from app.services.speech_recognition_service import SpeechRecognitionService
            from app.services.speech_service import SpeechService
            from app.services.context_memory_service import ContextMemoryService
            
            # Store wake word activation event
            context_memory = ContextMemoryService()
            await context_memory.store_system_event(
                event_type="wake_word",
                event_data={"activation_time": datetime.now().isoformat()}
            )
            
            # Give audio feedback that ARIA is listening
            speech_service = SpeechService()
            await speech_service.speak_with_fallback("Yes? I'm listening.")
            
            # Start listening for the actual command/question
            speech_recognition_service = SpeechRecognitionService()
            user_text = await speech_recognition_service.listen_for_speech(duration=8)
            
            if user_text:
                logger.info(f"User said after wake word: '{user_text}'")
                
                # Generate and speak response with wake_word conversation type
                from app.services.ai_service import AIService
                ai_service = AIService()
                response_text = await ai_service.generate_conversation_response(user_text, "wake_word")
                
                await speech_service.speak_with_fallback(response_text)
                
                logger.info("Wake word conversation completed successfully")
            else:
                # No speech detected after wake word
                await speech_service.speak_with_fallback("I didn't hear anything. Try again when you're ready.")
                
        except Exception as e:
            logger.error(f"Error handling wake word activation: {e}")
    
    async def test_wake_word_detection(self, duration: int = 5) -> Dict[str, Any]:
        """Test wake word detection with a recording."""
        try:
            logger.info(f"Testing wake word detection for {duration} seconds...")
            
            # Load model if not already loaded
            if not self.whisper_model:
                await self.load_whisper_model()
            
            if not self.whisper_model:
                return {
                    "success": False,
                    "message": "Whisper model not available for wake word detection"
                }
            
            # Record audio
            audio_file = await self._record_audio_chunk(duration)
            
            if not audio_file:
                return {
                    "success": False,
                    "message": "Failed to record audio"
                }
            
            # Detect wake word
            wake_word_detected = await self._detect_wake_word(audio_file)
            
            # Clean up
            if os.path.exists(audio_file):
                os.unlink(audio_file)
            
            return {
                "success": True,
                "wake_word_detected": wake_word_detected,
                "message": f"Wake word {'detected' if wake_word_detected else 'not detected'}",
                "wake_words": self.wake_words
            }
            
        except Exception as e:
            logger.error(f"Error testing wake word detection: {e}")
            return {
                "success": False,
                "message": f"Error testing wake word: {str(e)}"
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get wake word service status."""
        return {
            "enabled": self.enabled,
            "listening": self.listening,
            "wake_words": self.wake_words,
            "whisper_model_loaded": self.whisper_model is not None,
            "pyaudio_available": PYAUDIO_AVAILABLE,
            "whisper_available": WHISPER_AVAILABLE
        }
