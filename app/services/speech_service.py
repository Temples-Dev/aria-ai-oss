"""
Speech synthesis service for delivering audio greetings.
"""

import logging
import asyncio
import subprocess
from typing import Optional
import pyttsx3

from app.core.config import settings

logger = logging.getLogger(__name__)


class SpeechService:
    """Service for text-to-speech functionality."""
    
    def __init__(self):
        self.tts_engine = None
        self.enabled = settings.TTS_ENABLED
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize the TTS engine."""
        if not self.enabled:
            logger.info("TTS is disabled")
            return
        
        try:
            self.tts_engine = pyttsx3.init()
            
            # Configure voice settings
            self.tts_engine.setProperty('rate', settings.TTS_RATE)
            self.tts_engine.setProperty('volume', settings.TTS_VOLUME)
            
            # Set voice if specified
            if settings.TTS_VOICE:
                voices = self.tts_engine.getProperty('voices')
                for voice in voices:
                    if settings.TTS_VOICE.lower() in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
            
            logger.info("TTS engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize TTS engine: {e}")
            self.enabled = False
    
    async def speak(self, text: str) -> bool:
        """Speak the given text asynchronously."""
        if not self.enabled or not self.tts_engine:
            logger.warning("TTS not available, skipping speech")
            return False
        
        try:
            # Run TTS in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._speak_sync, text)
            return True
            
        except Exception as e:
            logger.error(f"Error during speech synthesis: {e}")
            return False
    
    def _speak_sync(self, text: str):
        """Synchronous speech synthesis."""
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
            
        except Exception as e:
            logger.error(f"Error in synchronous speech: {e}")
            raise
    
    async def speak_with_fallback(self, text: str) -> bool:
        """Speak text with fallback to system commands."""
        # Try primary TTS engine first
        if await self.speak(text):
            return True
        
        # Fallback to system TTS commands
        return await self._system_tts_fallback(text)
    
    async def _system_tts_fallback(self, text: str) -> bool:
        """Fallback to system TTS commands."""
        # Calculate espeak speed (espeak uses words per minute, but different scale)
        espeak_speed = max(80, min(200, int(settings.TTS_RATE * 0.8)))  # Convert and clamp
        
        tts_commands = [
            ['espeak', '-s', str(espeak_speed), '-a', '100', '-p', '50', text],  # speed, amplitude, pitch
            ['espeak-ng', '-s', str(espeak_speed), '-a', '100', '-p', '50', text],
            ['festival', '--tts'],
            ['spd-say', '-r', str(int(settings.TTS_RATE * 0.5)), text],  # spd-say uses different rate scale
        ]
        
        for cmd in tts_commands:
            try:
                if await self._try_system_command(cmd, text):
                    logger.info(f"Successfully used system TTS: {cmd[0]}")
                    return True
            except Exception as e:
                logger.debug(f"System TTS command {cmd[0]} failed: {e}")
                continue
        
        logger.warning("All TTS methods failed")
        return False
    
    async def _try_system_command(self, cmd: list, text: str) -> bool:
        """Try a system TTS command."""
        try:
            # Check if command exists
            check_cmd = ['which', cmd[0]]
            result = await asyncio.create_subprocess_exec(
                *check_cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await result.wait()
            
            if result.returncode != 0:
                return False
            
            # Execute TTS command
            if cmd[0] == 'festival':
                # Festival reads from stdin
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await process.communicate(input=text.encode())
            elif cmd[0] in ['espeak', 'espeak-ng']:
                # Espeak commands with parameters - text is the last argument
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await process.wait()
            else:
                # Other commands (spd-say, etc.)
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await process.wait()
            
            return process.returncode == 0
            
        except Exception as e:
            logger.debug(f"System command {cmd[0]} error: {e}")
            return False
    
    def test_speech(self) -> bool:
        """Test if speech synthesis is working."""
        if not self.enabled:
            return False
        
        try:
            test_text = "Speech test successful"
            self._speak_sync(test_text)
            return True
            
        except Exception as e:
            logger.error(f"Speech test failed: {e}")
            return False
    
    def get_available_voices(self) -> list:
        """Get list of available voices."""
        if not self.tts_engine:
            return []
        
        try:
            voices = self.tts_engine.getProperty('voices')
            return [{'id': v.id, 'name': v.name, 'lang': getattr(v, 'languages', [])} for v in voices]
            
        except Exception as e:
            logger.error(f"Error getting voices: {e}")
            return []
    
    def set_voice(self, voice_id: str) -> bool:
        """Set the TTS voice."""
        if not self.tts_engine:
            return False
        
        try:
            self.tts_engine.setProperty('voice', voice_id)
            return True
            
        except Exception as e:
            logger.error(f"Error setting voice: {e}")
            return False
    
    def set_rate(self, rate: int) -> bool:
        """Set the speech rate."""
        if not self.tts_engine:
            return False
        
        try:
            self.tts_engine.setProperty('rate', rate)
            return True
            
        except Exception as e:
            logger.error(f"Error setting rate: {e}")
            return False
