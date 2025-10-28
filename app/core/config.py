"""
Configuration settings for the Smart AI Boot Greeter.
"""

import os
from pydantic import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Server settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = False
    
    # AI Model settings
    OLLAMA_HOST: str = "http://localhost:11434"
    MODEL_NAME: str = "llama2:7b"  # Default to Llama2 7B
    
    # Speech settings
    TTS_ENABLED: bool = True
    TTS_RATE: int = 200  # Words per minute
    TTS_VOICE: Optional[str] = None  # System default
    
    # Boot monitoring settings
    BOOT_CHECK_INTERVAL: int = 5  # seconds
    BOOT_TIMEOUT: int = 300  # 5 minutes max wait
    
    # Context gathering settings
    WEATHER_API_KEY: Optional[str] = None
    LOCATION: str = "auto"  # auto-detect or specify city
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
