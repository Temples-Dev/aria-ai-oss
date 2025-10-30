"""
AI service for natural language processing using open-source models.
"""

import logging
import httpx
from typing import Dict, Any, Optional

from app.core.config import settings
from app.services.context_memory_service import ContextMemoryService

logger = logging.getLogger(__name__)


class AIService:
    """Service for interacting with open-source LLM via Ollama."""
    
    def __init__(self):
        self.ollama_url = settings.OLLAMA_HOST
        self.model_name = settings.MODEL_NAME
        self.client = httpx.AsyncClient(timeout=30.0)
        self.context_memory = ContextMemoryService()
    
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
            # Return a fallback greeting
            return self._fallback_greeting(context)
    
    async def generate_conversation_response(self, user_input: str, conversation_type: str = "voice") -> str:
        """
        Generate a conversational response to user input with context memory.
        
        Args:
            user_input: The user's message or question
            conversation_type: Type of conversation (voice, text, wake_word)
            
        Returns:
            AI-generated response
        """
        try:
            import time
            start_time = time.time()
            
            # Get conversation context from memory
            context = await self.context_memory.get_conversation_context()
            
            # Learn from this interaction
            await self.context_memory.learn_from_interaction(user_input, conversation_type)
            
            # Build context-aware prompt
            prompt = self._build_conversation_prompt(user_input, context)

            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 200
                }
            }
            
            response = await self.client.post(
                f"{self.ollama_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            ai_response = result.get("response", "").strip()
            
            # Clean and format the response
            ai_response = self._clean_response(ai_response)
            
            if not ai_response:
                ai_response = "I'm here to help! What would you like to know?"
            
            # Store conversation in memory
            response_time = int((time.time() - start_time) * 1000)
            await self.context_memory.store_conversation(
                user_input=user_input,
                aria_response=ai_response,
                conversation_type=conversation_type,
                response_time_ms=response_time
            )
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error generating conversation response: {e}")
            # Return a fallback response
            return "I'm sorry, I didn't quite catch that. Could you please repeat your question?"
    
    async def generate_unlock_welcome(self, context: Dict[str, Any]) -> str:
        """
        Generate a personalized welcome message for laptop unlock events.
        
        Args:
            context: Context information including unlock details, time, system info
            
        Returns:
            AI-generated welcome message
        """
        try:
            unlock_info = context.get('unlock', {})
            time_info = context.get('time', {})
            system_info = context.get('system', {})
            
            unlock_count = unlock_info.get('unlock_count', 1)
            session_duration = unlock_info.get('session_duration')
            hour = time_info.get('hour', 12)
            username = system_info.get('username', 'there')
            
            # Build context-aware prompt
            prompt = f"""You are ARIA, a friendly AI assistant. Generate a personalized welcome message for when the user unlocks their laptop.

Context:
- Time: {self._get_time_of_day_from_hour(hour)}
- User: {username}
- This is unlock #{unlock_count} today
- Session duration: {session_duration if session_duration else 'New session'}

Create a brief, natural welcome message that:
- Acknowledges the unlock/return
- Is contextually appropriate for the time of day
- Mentions relevant details if interesting (multiple unlocks, long session, etc.)
- Sounds natural when spoken aloud
- Is 1-2 sentences maximum

Examples:
- "Welcome back! Ready to continue your work?"
- "Good morning! I see you're starting your day."
- "Hello again! This is your third unlock today - staying busy?"

Your welcome message:"""

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
            welcome_message = result.get("response", "").strip()
            
            # Clean and format the response
            welcome_message = self._clean_response(welcome_message)
            
            if not welcome_message:
                return self._fallback_unlock_welcome(context)
            
            return welcome_message
            
        except Exception as e:
            logger.error(f"Error generating unlock welcome: {e}")
            return self._fallback_unlock_welcome(context)
    
    def _get_time_of_day_from_hour(self, hour: int) -> str:
        """Get time of day description from hour."""
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    def _fallback_unlock_welcome(self, context: Dict[str, Any]) -> str:
        """Generate a simple fallback welcome message."""
        unlock_info = context.get('unlock', {})
        time_info = context.get('time', {})
        system_info = context.get('system', {})
        
        unlock_count = unlock_info.get('unlock_count', 1)
        hour = time_info.get('hour', 12)
        username = system_info.get('username', 'there')
        
        time_of_day = self._get_time_of_day_from_hour(hour)
        
        if unlock_count == 1:
            return f"Good {time_of_day}, {username}! ARIA is ready to assist you."
        elif unlock_count <= 3:
            return f"Welcome back, {username}! Ready to continue?"
        else:
            return f"Hello again, {username}! Staying productive today, I see."
    
    def _build_conversation_prompt(self, user_input: str, context: Dict[str, Any]) -> str:
        """Build a context-aware conversation prompt."""
        recent_conversations = context.get("recent_conversations", [])
        user_preferences = context.get("user_preferences", {})
        session_info = context.get("session_info", {})
        
        # Build conversation history
        history_text = ""
        if recent_conversations:
            history_text = "\nRecent conversation context:\n"
            for conv in recent_conversations[-3:]:  # Last 3 conversations
                if conv.get("user_input") and conv.get("aria_response"):
                    history_text += f"User: {conv['user_input']}\nARIA: {conv['aria_response']}\n"
        
        # Build user context
        context_text = ""
        if user_preferences:
            greeting_style = user_preferences.get("greeting_style", {})
            if greeting_style.get("context_aware"):
                context_text += "\nUser prefers context-aware responses. "
            if not greeting_style.get("formal", True):
                context_text += "User prefers casual, friendly tone. "
        
        # Build session context
        session_text = ""
        if session_info:
            unlock_count = session_info.get("unlock_count", 0)
            if unlock_count > 1:
                session_text += f"\nThis is the user's {unlock_count} unlock today. "
        
        prompt = f"""You are ARIA, a friendly and helpful AI assistant. You have context about the user and previous conversations.

{history_text}{context_text}{session_text}

Current user message: {user_input}

Provide a helpful, conversational response that:
- Acknowledges any relevant context from previous conversations
- Maintains a natural, friendly tone
- Is concise but informative
- Shows you remember and learn from interactions

Your response:"""
        
        return prompt
    
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
        
        prompt = f"""You are ARIA, a friendly and helpful AI assistant that greets users when their computer boots up. ARIA stands for Adaptive Responsive Intelligence Assistant.

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
