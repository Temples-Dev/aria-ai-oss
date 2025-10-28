"""
Main greeting service that orchestrates context gathering, AI generation, and speech delivery.
"""

import logging
from typing import Dict, Any

from app.services.context_service import ContextService
from app.services.ai_service import AIService
from app.services.speech_service import SpeechService

logger = logging.getLogger(__name__)


class GreetingService:
    """Main service that orchestrates the greeting process."""
    
    def __init__(self):
        self.context_service = ContextService()
        self.ai_service = AIService()
        self.speech_service = SpeechService()
    
    async def deliver_boot_greeting(self) -> Dict[str, Any]:
        """Deliver a complete boot greeting with context, AI generation, and speech."""
        result = {
            'success': False,
            'greeting_text': '',
            'context': {},
            'speech_delivered': False,
            'error': None
        }
        
        try:
            logger.info("Starting boot greeting process...")
            
            # Step 1: Gather context
            logger.debug("Gathering context...")
            context = await self.context_service.gather_context()
            result['context'] = context
            
            # Step 2: Check if AI model is available
            model_available = await self.ai_service.check_model_availability()
            if not model_available:
                logger.warning(f"Model {self.ai_service.model_name} not available, attempting to pull...")
                pull_success = await self.ai_service.pull_model()
                if not pull_success:
                    logger.error("Failed to pull model, using fallback greeting")
            
            # Step 3: Generate greeting
            logger.debug("Generating greeting...")
            greeting_text = await self.ai_service.generate_greeting(context)
            result['greeting_text'] = greeting_text
            
            logger.info(f"Generated greeting: {greeting_text}")
            
            # Step 4: Deliver speech
            logger.debug("Delivering speech...")
            speech_success = await self.speech_service.speak_with_fallback(greeting_text)
            result['speech_delivered'] = speech_success
            
            if speech_success:
                logger.info("Greeting delivered successfully via speech")
            else:
                logger.warning("Speech delivery failed, greeting generated but not spoken")
            
            result['success'] = True
            
        except Exception as e:
            logger.error(f"Error in greeting delivery: {e}")
            result['error'] = str(e)
            
            # Try to deliver a simple fallback greeting
            try:
                fallback = self._get_simple_fallback()
                result['greeting_text'] = fallback
                speech_success = await self.speech_service.speak_with_fallback(fallback)
                result['speech_delivered'] = speech_success
                result['success'] = speech_success
                
            except Exception as fallback_error:
                logger.error(f"Even fallback greeting failed: {fallback_error}")
                result['error'] = f"Primary error: {e}, Fallback error: {fallback_error}"
        
        return result
    
    async def generate_greeting_only(self, context: Dict[str, Any] = None) -> str:
        """Generate a greeting without delivering it via speech."""
        try:
            if context is None:
                context = await self.context_service.gather_context()
            
            greeting = await self.ai_service.generate_greeting(context)
            return greeting
            
        except Exception as e:
            logger.error(f"Error generating greeting: {e}")
            return self._get_simple_fallback()
    
    async def test_all_services(self) -> Dict[str, bool]:
        """Test all services to ensure they're working."""
        results = {
            'context_service': False,
            'ai_service': False,
            'speech_service': False,
            'model_available': False
        }
        
        try:
            # Test context service
            context = await self.context_service.gather_context()
            results['context_service'] = bool(context)
            
            # Test AI service
            model_available = await self.ai_service.check_model_availability()
            results['model_available'] = model_available
            
            if model_available:
                test_greeting = await self.ai_service.generate_greeting(context)
                results['ai_service'] = bool(test_greeting)
            
            # Test speech service
            results['speech_service'] = self.speech_service.test_speech()
            
        except Exception as e:
            logger.error(f"Error testing services: {e}")
        
        return results
    
    def _get_simple_fallback(self) -> str:
        """Get a simple fallback greeting when all else fails."""
        import os
        from datetime import datetime
        
        username = os.getenv('USER', 'there')
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            return f"Good morning, {username}! Your system is ready."
        elif 12 <= hour < 17:
            return f"Good afternoon, {username}! Welcome back."
        elif 17 <= hour < 22:
            return f"Good evening, {username}! Your computer is all set."
        else:
            return f"Hello, {username}! Everything is ready to go."
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            await self.ai_service.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
