"""
AI service for natural language processing using open-source models.
"""

import logging
import httpx
from typing import Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """Service for interacting with open-source LLM via Ollama."""
    
    def __init__(self):
        self.ollama_url = settings.OLLAMA_HOST
        self.model_name = settings.MODEL_NAME
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def generate_greeting(self, context: Dict[str, Any]) -> str:
        """Generate a personalized greeting based on context."""
        try:
            prompt = self._build_greeting_prompt(context)
            response = await self._call_ollama(prompt)
            
            # Extract and clean the response
            greeting = self._clean_response(response)
            return greeting
            
        except Exception as e:
            logger.error(f"Error generating greeting: {e}")
            return self._fallback_greeting(context)
    
    def _build_greeting_prompt(self, context: Dict[str, Any]) -> str:
        """Build a prompt for greeting generation."""
        time_info = context.get('time', {})
        system_info = context.get('system', {})
        weather_info = context.get('weather', {})
        
        hour = time_info.get('hour', 12)
        day_name = time_info.get('day_name', 'today')
        username = system_info.get('username', 'there')
        
        # Determine time of day
        if 5 <= hour < 12:
            time_greeting = "Good morning"
        elif 12 <= hour < 17:
            time_greeting = "Good afternoon"
        elif 17 <= hour < 22:
            time_greeting = "Good evening"
        else:
            time_greeting = "Hello"
        
        prompt = f"""You are a friendly, helpful AI assistant that greets users when their computer boots up.

Generate a brief, warm, and natural greeting (1-2 sentences max) for the user based on this context:

Time: {time_greeting}, {day_name}
User: {username}
System: Linux boot completed
Weather: {weather_info.get('description', 'unknown')} {weather_info.get('temperature', '')}

Guidelines:
- Be warm and welcoming but not overly enthusiastic
- Keep it brief and natural
- Don't mention technical details about the boot process
- Make it feel personal but not intrusive
- Use natural, conversational language

Generate only the greeting text, no explanations or additional text:"""

        return prompt
    
    async def _call_ollama(self, prompt: str) -> str:
        """Make API call to Ollama."""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 100
                }
            }
            
            response = await self.client.post(
                f"{self.ollama_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except httpx.RequestError as e:
            logger.error(f"Network error calling Ollama: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Ollama: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Ollama: {e}")
            raise
    
    def _clean_response(self, response: str) -> str:
        """Clean and format the AI response."""
        # Remove common AI response artifacts
        cleaned = response.strip()
        
        # Remove quotes if the entire response is quoted
        if cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1]
        
        # Remove any leading/trailing whitespace or newlines
        cleaned = cleaned.strip()
        
        # Ensure it ends with appropriate punctuation
        if cleaned and not cleaned.endswith(('.', '!', '?')):
            cleaned += '.'
        
        return cleaned
    
    def _fallback_greeting(self, context: Dict[str, Any]) -> str:
        """Generate a simple fallback greeting if AI fails."""
        time_info = context.get('time', {})
        hour = time_info.get('hour', 12)
        username = context.get('system', {}).get('username', 'there')
        
        if 5 <= hour < 12:
            return f"Good morning, {username}! Your system is ready."
        elif 12 <= hour < 17:
            return f"Good afternoon, {username}! Welcome back."
        elif 17 <= hour < 22:
            return f"Good evening, {username}! Your computer is all set."
        else:
            return f"Hello, {username}! Everything is ready to go."
    
    async def check_model_availability(self) -> bool:
        """Check if the configured model is available in Ollama."""
        try:
            response = await self.client.get(f"{self.ollama_url}/api/tags")
            response.raise_for_status()
            
            models = response.json().get("models", [])
            available_models = [model["name"] for model in models]
            
            return self.model_name in available_models
            
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
            return False
    
    async def pull_model(self) -> bool:
        """Pull the configured model if it's not available."""
        try:
            logger.info(f"Pulling model {self.model_name}...")
            
            payload = {"name": self.model_name}
            response = await self.client.post(
                f"{self.ollama_url}/api/pull",
                json=payload
            )
            response.raise_for_status()
            
            logger.info(f"Successfully pulled model {self.model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
            return False
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
