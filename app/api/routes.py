"""
API routes for ARIA - Adaptive Responsive Intelligence Assistant.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.services.greeting_service import GreetingService
from app.services.context_service import ContextService
from app.services.ai_service import AIService
from app.services.speech_service import SpeechService
from app.services.speech_recognition_service import SpeechRecognitionService
from app.services.wake_word_service import WakeWordService
from app.services.unlock_detection_service import UnlockDetectionService
from app.services.context_memory_service import ContextMemoryService
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
            "message": f"Speech {'completed' if success else 'failed'}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error speaking text: {str(e)}")


@router.post("/speech/test-voice")
async def test_voice(voice: str = "kal_diphone"):
    """Test different Festival voices."""
    available_voices = [
        "kal_diphone", "rab_diphone",  # Original voices
        "cmu_us_slt_cg", "cmu_us_awb_cg", "cmu_us_rms_cg"  # New CMU voices
    ]
    
    if voice not in available_voices:
        raise HTTPException(
            status_code=400, 
            detail=f"Voice must be one of: {', '.join(available_voices)}"
        )
    
    speech_service = SpeechService()
    
    # Create descriptive text for each voice
    voice_descriptions = {
        "kal_diphone": "American English male voice",
        "rab_diphone": "British English male voice", 
        "cmu_us_slt_cg": "American English female voice",
        "cmu_us_awb_cg": "American English male voice - AWB",
        "cmu_us_rms_cg": "American English male voice - RMS"
    }
    
    description = voice_descriptions.get(voice, voice.replace('_', ' '))
    test_text = f"Hello! I am ARIA speaking with the {description}. How do I sound?"
    
    try:
        success = await speech_service._festival_tts(test_text, voice)
        
        return {
            "success": success,
            "message": f"Voice test completed with {voice}",
            "voice_used": voice,
            "voice_description": description,
            "test_text": test_text,
            "available_voices": available_voices
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing voice: {str(e)}")


@router.get("/speech/voices/festival")
async def list_festival_voices():
    """List all available Festival voices with descriptions."""
    voices = {
        "kal_diphone": {
            "name": "kal_diphone",
            "description": "American English male voice",
            "gender": "male",
            "accent": "american",
            "quality": "diphone"
        },
        "rab_diphone": {
            "name": "rab_diphone", 
            "description": "British English male voice",
            "gender": "male",
            "accent": "british",
            "quality": "diphone"
        },
        "cmu_us_slt_cg": {
            "name": "cmu_us_slt_cg",
            "description": "American English female voice",
            "gender": "female", 
            "accent": "american",
            "quality": "clustergen"
        },
        "cmu_us_awb_cg": {
            "name": "cmu_us_awb_cg",
            "description": "American English male voice - AWB",
            "gender": "male",
            "accent": "american", 
            "quality": "clustergen"
        },
        "cmu_us_rms_cg": {
            "name": "cmu_us_rms_cg",
            "description": "American English male voice - RMS", 
            "gender": "male",
            "accent": "american",
            "quality": "clustergen"
        }
    }
    
    return {
        "voices": voices,
        "current_voice": settings.TTS_FESTIVAL_VOICE,
        "total_count": len(voices)
    }


@router.post("/conversation/voice")
async def voice_conversation():
    """Start a voice conversation with ARIA - listen for speech and respond."""
    speech_recognition_service = SpeechRecognitionService()
    
    try:
        result = await speech_recognition_service.start_conversation_mode()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in voice conversation: {str(e)}")


@router.post("/conversation/listen")
async def listen_for_speech(duration: int = 5):
    """Listen for speech and return the recognized text."""
    if duration < 1 or duration > 30:
        raise HTTPException(status_code=400, detail="Duration must be between 1 and 30 seconds")
    
    speech_recognition_service = SpeechRecognitionService()
    
    try:
        recognized_text = await speech_recognition_service.listen_for_speech(duration)
        
        return {
            "success": recognized_text is not None,
            "text": recognized_text,
            "message": "Speech recognized successfully" if recognized_text else "No speech detected",
            "duration": duration
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in speech recognition: {str(e)}")


@router.post("/conversation/respond")
async def respond_to_text(text: str):
    """Generate an AI response to text and speak it."""
    if not text or len(text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    if len(text) > 500:
        raise HTTPException(status_code=400, detail="Text too long (max 500 characters)")
    
    try:
        # Generate AI response
        ai_service = AIService()
        response_text = await ai_service.generate_conversation_response(text)
        
        # Speak the response
        speech_service = SpeechService()
        speech_success = await speech_service.speak_with_fallback(response_text)
        
        return {
            "success": True,
            "user_input": text,
            "aria_response": response_text,
            "speech_delivered": speech_success,
            "message": "Response generated and spoken successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


@router.post("/wake-word/start")
async def start_wake_word_listening():
    """Start continuous wake word listening."""
    wake_word_service = WakeWordService()
    
    try:
        await wake_word_service.start_continuous_listening()
        
        return {
            "success": True,
            "message": "Wake word listening started",
            "status": wake_word_service.get_status()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting wake word listening: {str(e)}")


@router.post("/wake-word/stop")
async def stop_wake_word_listening():
    """Stop continuous wake word listening."""
    wake_word_service = WakeWordService()
    
    try:
        await wake_word_service.stop_continuous_listening()
        
        return {
            "success": True,
            "message": "Wake word listening stopped",
            "status": wake_word_service.get_status()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping wake word listening: {str(e)}")


@router.get("/wake-word/status")
async def get_wake_word_status():
    """Get wake word service status."""
    wake_word_service = WakeWordService()
    
    return {
        "success": True,
        "status": wake_word_service.get_status()
    }


@router.post("/wake-word/test")
async def test_wake_word_detection(duration: int = 5):
    """Test wake word detection."""
    if duration < 1 or duration > 10:
        raise HTTPException(status_code=400, detail="Duration must be between 1 and 10 seconds")
    
    wake_word_service = WakeWordService()
    
    try:
        result = await wake_word_service.test_wake_word_detection(duration)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing wake word: {str(e)}")


@router.post("/unlock-detection/start")
async def start_unlock_detection():
    """Start unlock detection monitoring."""
    unlock_service = UnlockDetectionService()
    
    try:
        # Register welcome message callback
        unlock_service.add_unlock_callback(unlock_service.trigger_welcome_message)
        
        # Start monitoring
        await unlock_service.start_monitoring()
        
        return {
            "success": True,
            "message": "Unlock detection started",
            "status": unlock_service.get_status()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting unlock detection: {str(e)}")


@router.post("/unlock-detection/stop")
async def stop_unlock_detection():
    """Stop unlock detection monitoring."""
    unlock_service = UnlockDetectionService()
    
    try:
        await unlock_service.stop_monitoring()
        
        return {
            "success": True,
            "message": "Unlock detection stopped",
            "status": unlock_service.get_status()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping unlock detection: {str(e)}")


@router.get("/unlock-detection/status")
async def get_unlock_detection_status():
    """Get unlock detection service status."""
    unlock_service = UnlockDetectionService()
    
    return {
        "success": True,
        "status": unlock_service.get_status()
    }


@router.post("/unlock-detection/test")
async def test_unlock_detection():
    """Test unlock detection by simulating an unlock event."""
    unlock_service = UnlockDetectionService()
    
    try:
        # Register welcome message callback for test
        unlock_service.add_unlock_callback(unlock_service.trigger_welcome_message)
        
        result = await unlock_service.test_unlock_detection()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing unlock detection: {str(e)}")


@router.get("/memory/conversations")
async def get_recent_conversations(limit: int = 10):
    """Get recent conversations from memory."""
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 50")
    
    context_memory = ContextMemoryService()
    
    try:
        conversations = await context_memory.get_recent_conversations(limit)
        
        return {
            "success": True,
            "conversations": conversations,
            "count": len(conversations)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting conversations: {str(e)}")


@router.get("/memory/context/{context_key}")
async def get_user_context(context_key: str):
    """Get user context by key."""
    context_memory = ContextMemoryService()
    
    try:
        context_value = await context_memory.get_user_context(context_key)
        
        if context_value is None:
            raise HTTPException(status_code=404, detail=f"Context key '{context_key}' not found")
        
        return {
            "success": True,
            "context_key": context_key,
            "context_value": context_value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting context: {str(e)}")


@router.post("/memory/context/{context_key}")
async def set_user_context(context_key: str, context_data: Dict[str, Any]):
    """Set user context."""
    context_memory = ContextMemoryService()
    
    try:
        context_value = context_data.get("context_value")
        context_type = context_data.get("context_type", "preference")
        importance_score = context_data.get("importance_score", 5)
        
        if context_value is None:
            raise HTTPException(status_code=400, detail="context_value is required")
        
        success = await context_memory.set_user_context(
            context_key=context_key,
            context_value=context_value,
            context_type=context_type,
            importance_score=importance_score
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to set context")
        
        return {
            "success": True,
            "message": f"Context '{context_key}' updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting context: {str(e)}")


@router.get("/memory/status")
async def get_memory_status():
    """Get context memory service status."""
    context_memory = ContextMemoryService()
    
    return {
        "success": True,
        "status": context_memory.get_status()
    }


@router.get("/memory/conversation-context")
async def get_conversation_context():
    """Get full conversation context for AI responses."""
    context_memory = ContextMemoryService()
    
    try:
        context = await context_memory.get_conversation_context()
        
        return {
            "success": True,
            "context": context
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting conversation context: {str(e)}")
