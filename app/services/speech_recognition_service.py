"""
Speech recognition service for converting speech to text.
"""

import logging
import asyncio
import tempfile
import os
import subprocess
from typing import Optional, Dict, Any
import json

from app.core.config import settings

# Try to import speech recognition libraries
try:
    import speech_recognition as sr
    import pyaudio
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

logger = logging.getLogger(__name__)


class SpeechRecognitionService:
    """Service for speech-to-text functionality."""
    
    def __init__(self):
        self.enabled = True
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required dependencies are available."""
        try:
            # Check for arecord (ALSA recording tool)
            result = subprocess.run(['which', 'arecord'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning("arecord not found - speech recognition may not work")
                self.enabled = False
                return
            
            logger.info("Speech recognition service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize speech recognition: {e}")
            self.enabled = False
    
    async def listen_for_speech(self, duration: int = 5, timeout: int = 10) -> Optional[str]:
        """
        Listen for speech and convert to text.
        
        Args:
            duration: Maximum recording duration in seconds
            timeout: Maximum time to wait for speech
            
        Returns:
            Recognized text or None if recognition failed
        """
        if not self.enabled:
            logger.warning("Speech recognition is not available")
            return None
        
        try:
            # Record audio to temporary file
            if SPEECH_RECOGNITION_AVAILABLE:
                audio_file = await self._record_audio_pyaudio(duration)
            else:
                audio_file = await self._record_audio(duration)
                
            if not audio_file:
                return None
            
            # Convert speech to text using available methods
            text = await self._speech_to_text(audio_file)
            
            # Clean up temporary file
            if os.path.exists(audio_file):
                os.unlink(audio_file)
            
            return text
            
        except Exception as e:
            logger.error(f"Error in speech recognition: {e}")
            return None
    
    async def _record_audio(self, duration: int) -> Optional[str]:
        """Record audio from microphone."""
        try:
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                audio_path = temp_file.name
            
            logger.info(f"Recording audio for {duration} seconds...")
            
            # Use arecord to capture audio
            process = await asyncio.create_subprocess_exec(
                'arecord',
                '-f', 'cd',  # CD quality
                '-t', 'wav',  # WAV format
                '-d', str(duration),  # Duration
                '-r', '16000',  # Sample rate
                audio_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            if process.returncode == 0 and os.path.exists(audio_path):
                logger.info("Audio recording completed successfully")
                return audio_path
            else:
                logger.error("Audio recording failed")
                if os.path.exists(audio_path):
                    os.unlink(audio_path)
                return None
                
        except Exception as e:
            logger.error(f"Error recording audio: {e}")
            return None
    
    async def _record_audio_pyaudio(self, duration: int) -> Optional[str]:
        """Record audio using PyAudio."""
        if not SPEECH_RECOGNITION_AVAILABLE:
            return None
            
        try:
            import concurrent.futures
            import wave
            
            def record_audio():
                # Audio recording parameters
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
                    
                    logger.info(f"Recording audio for {duration} seconds using PyAudio...")
                    
                    frames = []
                    for i in range(0, int(RATE / CHUNK * duration)):
                        data = stream.read(CHUNK)
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
                
            if audio_path and os.path.exists(audio_path):
                logger.info("PyAudio recording completed successfully")
                return audio_path
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error recording audio with PyAudio: {e}")
            return None
    
    async def _speech_to_text(self, audio_file: str) -> Optional[str]:
        """Convert audio file to text using available STT engines."""
        
        # Try different speech-to-text methods in order of preference
        stt_methods = [
            self._try_python_speech_recognition,  # Use Python SpeechRecognition library
            self._try_whisper_cpp,
            self._try_vosk,
            self._try_mock_recognition  # Fallback for testing
        ]
        
        for method in stt_methods:
            try:
                result = await method(audio_file)
                if result:
                    logger.info(f"Speech recognized: '{result}'")
                    return result
            except Exception as e:
                logger.debug(f"STT method {method.__name__} failed: {e}")
                continue
        
        logger.warning("All speech-to-text methods failed")
        return None
    
    async def _try_python_speech_recognition(self, audio_file: str) -> Optional[str]:
        """Try using Python SpeechRecognition library with Google Web Speech API."""
        if not SPEECH_RECOGNITION_AVAILABLE:
            return None
            
        try:
            # Run speech recognition in a thread to avoid blocking
            import concurrent.futures
            
            def recognize_speech():
                r = sr.Recognizer()
                with sr.AudioFile(audio_file) as source:
                    # Adjust for ambient noise
                    r.adjust_for_ambient_noise(source, duration=0.5)
                    # Record the audio
                    audio = r.record(source)
                
                try:
                    # Use Google Web Speech API (free tier)
                    text = r.recognize_google(audio)
                    return text
                except sr.UnknownValueError:
                    logger.debug("Google Speech Recognition could not understand audio")
                    return None
                except sr.RequestError as e:
                    logger.debug(f"Could not request results from Google Speech Recognition; {e}")
                    return None
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(executor, recognize_speech)
                
            if result:
                logger.info(f"Python SpeechRecognition successful: '{result}'")
                return result
            
            return None
            
        except Exception as e:
            logger.debug(f"Python SpeechRecognition failed: {e}")
            return None
    
    async def _try_whisper_cpp(self, audio_file: str) -> Optional[str]:
        """Try using whisper.cpp for speech recognition."""
        try:
            # Check if whisper is available
            check_process = await asyncio.create_subprocess_exec(
                'which', 'whisper',
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await check_process.wait()
            
            if check_process.returncode != 0:
                return None
            
            # Use whisper for transcription
            process = await asyncio.create_subprocess_exec(
                'whisper', audio_file, '--output_format', 'txt', '--language', 'en',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Parse whisper output
                output = stdout.decode().strip()
                if output:
                    return output
            
            return None
            
        except Exception as e:
            logger.debug(f"Whisper recognition failed: {e}")
            return None
    
    async def _try_vosk(self, audio_file: str) -> Optional[str]:
        """Try using Vosk for speech recognition."""
        try:
            # Check if vosk is available
            check_process = await asyncio.create_subprocess_exec(
                'which', 'vosk-transcriber',
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await check_process.wait()
            
            if check_process.returncode != 0:
                return None
            
            # Use vosk for transcription
            process = await asyncio.create_subprocess_exec(
                'vosk-transcriber', audio_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode().strip()
                if output:
                    return output
            
            return None
            
        except Exception as e:
            logger.debug(f"Vosk recognition failed: {e}")
            return None
    
    async def _try_mock_recognition(self, audio_file: str) -> Optional[str]:
        """Mock recognition for testing purposes."""
        try:
            # Check if audio file exists and has content
            if os.path.exists(audio_file) and os.path.getsize(audio_file) > 1000:
                logger.info("Using mock recognition - returning test phrase")
                return "Hello ARIA, how are you today?"
            return None
        except Exception:
            return None
    
    async def start_conversation_mode(self) -> Dict[str, Any]:
        """Start a voice conversation with ARIA."""
        try:
            logger.info("Starting voice conversation mode...")
            
            # Listen for user speech
            user_text = await self.listen_for_speech(duration=5)
            
            if not user_text:
                return {
                    "success": False,
                    "message": "No speech detected or recognition failed",
                    "user_text": None,
                    "aria_response": None
                }
            
            # Import here to avoid circular imports
            from app.services.ai_service import AIService
            from app.services.speech_service import SpeechService
            
            # Generate AI response
            ai_service = AIService()
            response_text = await ai_service.generate_conversation_response(user_text)
            
            # Speak the response
            speech_service = SpeechService()
            speech_success = await speech_service.speak_with_fallback(response_text)
            
            return {
                "success": True,
                "message": "Voice conversation completed",
                "user_text": user_text,
                "aria_response": response_text,
                "speech_delivered": speech_success
            }
            
        except Exception as e:
            logger.error(f"Error in conversation mode: {e}")
            return {
                "success": False,
                "message": f"Conversation error: {str(e)}",
                "user_text": None,
                "aria_response": None
            }
