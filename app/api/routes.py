"""
API routes for ARIA - Adaptive Responsive Intelligence Assistant.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.services.greeting_service import GreetingService
from app.services.context_service import ContextService
from app.services.ai_service import AIService
from app.services.speech_service import SpeechService
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ARIA - Adaptive Responsive Intelligence Assistant"}


@router.post("/greeting/deliver")
async def deliver_greeting():
    """Manually trigger a boot greeting."""
    greeting_service = GreetingService()
    
    try:
        result = await greeting_service.deliver_boot_greeting()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error delivering greeting: {str(e)}")
    finally:
        await greeting_service.cleanup()


@router.get("/greeting/generate")
async def generate_greeting():
    """Generate a greeting without speaking it."""
    greeting_service = GreetingService()
    
    try:
        greeting_text = await greeting_service.generate_greeting_only()
        context = await greeting_service.context_service.gather_context()
        
        return {
            "greeting": greeting_text,
            "context": context,
            "timestamp": context.get("time", {}).get("formatted_time", "unknown")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating greeting: {str(e)}")
    finally:
        await greeting_service.cleanup()


@router.get("/context")
async def get_context():
    """Get current system context."""
    context_service = ContextService()
    
    try:
        context = await context_service.gather_context()
        return context
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error gathering context: {str(e)}")


@router.get("/services/test")
async def test_services():
    """Test all services to ensure they're working."""
    greeting_service = GreetingService()
    
    try:
        results = await greeting_service.test_all_services()
        return {
            "test_results": results,
            "overall_status": "healthy" if all(results.values()) else "degraded"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing services: {str(e)}")
    finally:
        await greeting_service.cleanup()


@router.get("/ai/models")
async def get_model_info():
    """Get information about the AI model."""
    ai_service = AIService()
    
    try:
        model_available = await ai_service.check_model_availability()
        
        return {
            "model_name": ai_service.model_name,
            "ollama_host": ai_service.ollama_url,
            "model_available": model_available
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking model: {str(e)}")
    finally:
        await ai_service.close()


@router.post("/ai/models/pull")
async def pull_model():
    """Pull the configured AI model."""
    ai_service = AIService()
    
    try:
        success = await ai_service.pull_model()
        
        if success:
            return {"message": f"Successfully pulled model {ai_service.model_name}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to pull model")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error pulling model: {str(e)}")
    finally:
        await ai_service.close()


@router.get("/speech/voices")
async def get_voices():
    """Get available TTS voices."""
    speech_service = SpeechService()
    
    try:
        voices = speech_service.get_available_voices()
        return {
            "voices": voices,
            "tts_enabled": speech_service.enabled
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting voices: {str(e)}")


@router.post("/speech/test")
async def test_speech():
    """Test speech synthesis."""
    speech_service = SpeechService()
    
    try:
        success = await speech_service.speak_with_fallback("This is a test of the speech system.")
        
        return {
            "success": success,
            "message": "Speech test completed" if success else "Speech test failed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing speech: {str(e)}")


@router.post("/speech/test-quality")
async def test_speech_quality():
    """Test speech with a longer sample to check quality and speed."""
    speech_service = SpeechService()
    
    test_text = """Hello! I am ARIA, your adaptive responsive intelligence assistant. 
    I am speaking at a comfortable pace so you can clearly understand every word I say. 
    This test helps ensure my speech quality is optimal for daily interactions."""
    
    try:
        success = await speech_service.speak_with_fallback(test_text)
        
        return {
            "success": success,
            "message": "Speech quality test completed",
            "test_text": test_text,
            "settings": {
                "rate": settings.TTS_RATE,
                "volume": settings.TTS_VOLUME
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in speech quality test: {str(e)}")


@router.post("/speech/say")
async def speak_text(text: str):
    """Speak the provided text."""
    if not text or len(text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    if len(text) > 500:
        raise HTTPException(status_code=400, detail="Text too long (max 500 characters)")
    
    speech_service = SpeechService()
    
    try:
        success = await speech_service.speak_with_fallback(text)
        
        return {
            "success": success,
            "text": text,
            "message": "Text spoken successfully" if success else "Failed to speak text"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error speaking text: {str(e)}")
