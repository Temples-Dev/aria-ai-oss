"""
Context memory service for ARIA - handles conversation history, user preferences, and learning.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.config import settings

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Database imports
from app.database.database import get_db, SessionLocal
from app.database.models import (
    Session as DBSession, 
    Conversation, 
    UserContext, 
    SystemEvent, 
    InteractionPattern
)

logger = logging.getLogger(__name__)


class ContextMemoryService:
    """Service for managing context memory with Redis cache and PostgreSQL persistence."""
    
    def __init__(self):
        self.redis_client = None
        self.enabled = True
        self.user_id = "default_user"  # Can be made configurable later
        self._setup_redis()
    
    def _setup_redis(self):
        """Setup Redis connection."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available - using memory-only cache")
            return
        
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None
    
    async def store_conversation(
        self, 
        user_input: str, 
        aria_response: str, 
        conversation_type: str = "voice",
        context_data: Dict[str, Any] = None,
        response_time_ms: int = None,
        session_id: str = None
    ) -> str:
        """
        Store a conversation in both Redis (hot cache) and PostgreSQL (persistent).
        
        Returns:
            Conversation ID
        """
        try:
            db = SessionLocal()
            
            # Get or create current session
            if not session_id:
                session_id = await self._get_current_session_id(db)
            
            # Create conversation record
            conversation = Conversation(
                session_id=session_id,
                user_id=self.user_id,
                conversation_type=conversation_type,
                user_input=user_input,
                aria_response=aria_response,
                context_data=context_data or {},
                response_time_ms=response_time_ms,
                success=True
            )
            
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            
            conversation_id = str(conversation.id)
            
            # Store in Redis cache for quick access
            if self.redis_client:
                await self._cache_recent_conversation(conversation)
            
            # Update interaction patterns
            await self._update_interaction_patterns(user_input, conversation_type, db)
            
            logger.info(f"Stored conversation {conversation_id}")
            return conversation_id
            
        except Exception as e:
            logger.error(f"Error storing conversation: {e}")
            if 'db' in locals():
                db.rollback()
            return None
        finally:
            if 'db' in locals():
                db.close()
    
    async def get_recent_conversations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversations from cache or database."""
        try:
            # Try Redis first for speed
            if self.redis_client:
                cached_conversations = await self._get_cached_conversations(limit)
                if cached_conversations:
                    return cached_conversations
            
            # Fallback to database
            db = SessionLocal()
            conversations = db.query(Conversation)\
                .filter_by(user_id=self.user_id)\
                .order_by(desc(Conversation.timestamp))\
                .limit(limit)\
                .all()
            
            result = []
            for conv in conversations:
                result.append({
                    "id": str(conv.id),
                    "user_input": conv.user_input,
                    "aria_response": conv.aria_response,
                    "conversation_type": conv.conversation_type,
                    "timestamp": conv.timestamp.isoformat(),
                    "context_data": conv.context_data,
                    "response_time_ms": conv.response_time_ms
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting recent conversations: {e}")
            return []
        finally:
            if 'db' in locals():
                db.close()
    
    async def get_user_context(self, context_key: str) -> Optional[Dict[str, Any]]:
        """Get user context by key from cache or database."""
        try:
            # Try Redis cache first
            if self.redis_client:
                cached_value = self.redis_client.get(f"user_context:{self.user_id}:{context_key}")
                if cached_value:
                    return json.loads(cached_value)
            
            # Get from database
            db = SessionLocal()
            context = db.query(UserContext)\
                .filter_by(user_id=self.user_id, context_key=context_key)\
                .first()
            
            if context:
                # Update access tracking
                context.last_accessed = datetime.utcnow()
                context.access_count += 1
                db.commit()
                
                # Cache in Redis
                if self.redis_client:
                    self.redis_client.setex(
                        f"user_context:{self.user_id}:{context_key}",
                        3600,  # 1 hour TTL
                        json.dumps(context.context_value)
                    )
                
                return context.context_value
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user context {context_key}: {e}")
            return None
        finally:
            if 'db' in locals():
                db.close()
    
    async def set_user_context(
        self, 
        context_key: str, 
        context_value: Dict[str, Any], 
        context_type: str = "preference",
        importance_score: int = 5
    ) -> bool:
        """Set user context in both cache and database."""
        try:
            db = SessionLocal()
            
            # Update or create context
            context = db.query(UserContext)\
                .filter_by(user_id=self.user_id, context_key=context_key)\
                .first()
            
            if context:
                context.context_value = context_value
                context.context_type = context_type
                context.importance_score = importance_score
                context.last_accessed = datetime.utcnow()
                context.access_count += 1
            else:
                context = UserContext(
                    user_id=self.user_id,
                    context_key=context_key,
                    context_value=context_value,
                    context_type=context_type,
                    importance_score=importance_score
                )
                db.add(context)
            
            db.commit()
            
            # Update Redis cache
            if self.redis_client:
                self.redis_client.setex(
                    f"user_context:{self.user_id}:{context_key}",
                    3600,  # 1 hour TTL
                    json.dumps(context_value)
                )
            
            logger.info(f"Updated user context: {context_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting user context {context_key}: {e}")
            if 'db' in locals():
                db.rollback()
            return False
        finally:
            if 'db' in locals():
                db.close()
    
    async def store_system_event(
        self, 
        event_type: str, 
        event_data: Dict[str, Any] = None,
        response_text: str = None,
        session_id: str = None
    ) -> str:
        """Store system events like unlock, wake_word activation."""
        try:
            db = SessionLocal()
            
            if not session_id:
                session_id = await self._get_current_session_id(db)
            
            event = SystemEvent(
                session_id=session_id,
                user_id=self.user_id,
                event_type=event_type,
                event_data=event_data or {},
                response_generated=bool(response_text),
                response_text=response_text
            )
            
            db.add(event)
            db.commit()
            db.refresh(event)
            
            # Cache recent events in Redis
            if self.redis_client:
                event_data_cache = {
                    "id": str(event.id),
                    "event_type": event_type,
                    "event_data": event_data or {},
                    "timestamp": event.timestamp.isoformat(),
                    "response_text": response_text
                }
                
                self.redis_client.lpush(
                    f"recent_events:{self.user_id}",
                    json.dumps(event_data_cache)
                )
                self.redis_client.ltrim(f"recent_events:{self.user_id}", 0, 49)  # Keep last 50
            
            logger.info(f"Stored system event: {event_type}")
            return str(event.id)
            
        except Exception as e:
            logger.error(f"Error storing system event: {e}")
            if 'db' in locals():
                db.rollback()
            return None
        finally:
            if 'db' in locals():
                db.close()
    
    async def get_conversation_context(self, limit: int = 5) -> Dict[str, Any]:
        """Get contextual information for AI responses."""
        try:
            # Get recent conversations
            recent_conversations = await self.get_recent_conversations(limit)
            
            # Get user preferences
            voice_prefs = await self.get_user_context("voice_preference") or {}
            greeting_style = await self.get_user_context("greeting_style") or {}
            interaction_history = await self.get_user_context("interaction_history") or {}
            
            # Get session info
            db = SessionLocal()
            current_session = await self._get_current_session(db)
            
            context = {
                "recent_conversations": recent_conversations,
                "user_preferences": {
                    "voice": voice_prefs,
                    "greeting_style": greeting_style,
                    "interaction_history": interaction_history
                },
                "session_info": {
                    "session_id": str(current_session.id) if current_session else None,
                    "unlock_count": current_session.unlock_count if current_session else 0,
                    "total_interactions": current_session.total_interactions if current_session else 0,
                    "session_start": current_session.session_start.isoformat() if current_session else None
                }
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return {}
        finally:
            if 'db' in locals():
                db.close()
    
    async def learn_from_interaction(self, user_input: str, conversation_type: str):
        """Learn patterns from user interactions."""
        try:
            db = SessionLocal()
            
            # Extract topics/keywords from user input
            topics = self._extract_topics(user_input)
            
            # Update interaction patterns
            for topic in topics:
                pattern = db.query(InteractionPattern)\
                    .filter_by(user_id=self.user_id, pattern_type="topic_interest")\
                    .filter(InteractionPattern.pattern_data.contains({"topic": topic}))\
                    .first()
                
                if pattern:
                    pattern.frequency += 1
                    pattern.last_occurrence = datetime.utcnow()
                    pattern.confidence_score = min(1.0, pattern.confidence_score + 0.1)
                else:
                    pattern = InteractionPattern(
                        user_id=self.user_id,
                        pattern_type="topic_interest",
                        pattern_data={"topic": topic},
                        frequency=1,
                        confidence_score=0.5
                    )
                    db.add(pattern)
            
            # Update time-based patterns
            current_hour = datetime.now().hour
            time_pattern = db.query(InteractionPattern)\
                .filter_by(user_id=self.user_id, pattern_type="active_hours")\
                .first()
            
            if time_pattern:
                hours_data = time_pattern.pattern_data.get("hours", {})
                hours_data[str(current_hour)] = hours_data.get(str(current_hour), 0) + 1
                time_pattern.pattern_data = {"hours": hours_data}
                time_pattern.frequency += 1
            else:
                time_pattern = InteractionPattern(
                    user_id=self.user_id,
                    pattern_type="active_hours",
                    pattern_data={"hours": {str(current_hour): 1}},
                    frequency=1
                )
                db.add(time_pattern)
            
            db.commit()
            logger.info("Updated interaction patterns from learning")
            
        except Exception as e:
            logger.error(f"Error learning from interaction: {e}")
            if 'db' in locals():
                db.rollback()
        finally:
            if 'db' in locals():
                db.close()
    
    async def _get_current_session_id(self, db: Session) -> str:
        """Get or create current session."""
        session = await self._get_current_session(db)
        return str(session.id)
    
    async def _get_current_session(self, db: Session) -> DBSession:
        """Get or create current session."""
        # Look for active session (within last 4 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=4)
        session = db.query(DBSession)\
            .filter_by(user_id=self.user_id)\
            .filter(DBSession.session_start >= cutoff_time)\
            .filter(DBSession.session_end.is_(None))\
            .first()
        
        if not session:
            # Create new session
            session = DBSession(
                user_id=self.user_id,
                session_start=datetime.utcnow(),
                session_data={"created_by": "context_memory_service"}
            )
            db.add(session)
            db.commit()
            db.refresh(session)
        
        return session
    
    async def _cache_recent_conversation(self, conversation: Conversation):
        """Cache conversation in Redis for quick access."""
        if not self.redis_client:
            return
        
        try:
            conv_data = {
                "id": str(conversation.id),
                "user_input": conversation.user_input,
                "aria_response": conversation.aria_response,
                "conversation_type": conversation.conversation_type,
                "timestamp": conversation.timestamp.isoformat(),
                "context_data": conversation.context_data
            }
            
            # Add to recent conversations list
            self.redis_client.lpush(
                f"recent_conversations:{self.user_id}",
                json.dumps(conv_data)
            )
            
            # Keep only last 20 conversations in cache
            self.redis_client.ltrim(f"recent_conversations:{self.user_id}", 0, 19)
            
        except Exception as e:
            logger.error(f"Error caching conversation: {e}")
    
    async def _get_cached_conversations(self, limit: int) -> List[Dict[str, Any]]:
        """Get conversations from Redis cache."""
        if not self.redis_client:
            return []
        
        try:
            cached_data = self.redis_client.lrange(
                f"recent_conversations:{self.user_id}", 
                0, 
                limit - 1
            )
            
            conversations = []
            for data in cached_data:
                conversations.append(json.loads(data))
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting cached conversations: {e}")
            return []
    
    async def _update_interaction_patterns(self, user_input: str, conversation_type: str, db: Session):
        """Update interaction patterns based on user input."""
        try:
            # Update conversation type frequency
            type_pattern = db.query(InteractionPattern)\
                .filter_by(user_id=self.user_id, pattern_type="conversation_types")\
                .first()
            
            if type_pattern:
                types_data = type_pattern.pattern_data.get("types", {})
                types_data[conversation_type] = types_data.get(conversation_type, 0) + 1
                type_pattern.pattern_data = {"types": types_data}
                type_pattern.frequency += 1
            else:
                type_pattern = InteractionPattern(
                    user_id=self.user_id,
                    pattern_type="conversation_types",
                    pattern_data={"types": {conversation_type: 1}},
                    frequency=1
                )
                db.add(type_pattern)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error updating interaction patterns: {e}")
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics/keywords from text."""
        if not text:
            return []
        
        # Simple keyword extraction (can be enhanced with NLP later)
        keywords = {
            "time": ["time", "clock", "hour", "minute", "when"],
            "weather": ["weather", "temperature", "rain", "sunny", "cloudy"],
            "greeting": ["hello", "hi", "good morning", "good afternoon", "good evening"],
            "help": ["help", "assist", "support", "how to"],
            "music": ["music", "song", "play", "listen"],
            "reminder": ["remind", "remember", "schedule", "appointment"],
            "question": ["what", "how", "why", "where", "when", "who"]
        }
        
        text_lower = text.lower()
        found_topics = []
        
        for topic, words in keywords.items():
            if any(word in text_lower for word in words):
                found_topics.append(topic)
        
        return found_topics
    
    def get_status(self) -> Dict[str, Any]:
        """Get context memory service status."""
        return {
            "enabled": self.enabled,
            "redis_connected": self.redis_client is not None,
            "user_id": self.user_id,
            "redis_available": REDIS_AVAILABLE
        }
