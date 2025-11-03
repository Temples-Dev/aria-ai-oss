"""
SQLAlchemy models for ARIA database.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.database import Base


class Session(Base):
    """User session model."""
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, default="default_user", index=True)
    session_start = Column(DateTime(timezone=True), nullable=False, default=func.now())
    session_end = Column(DateTime(timezone=True), nullable=True)
    unlock_count = Column(Integer, default=0)
    total_interactions = Column(Integer, default=0)
    last_activity = Column(DateTime(timezone=True), default=func.now())
    session_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    conversations = relationship("Conversation", back_populates="session", cascade="all, delete-orphan")
    system_events = relationship("SystemEvent", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, start={self.session_start})>"


class Conversation(Base):
    """Conversation history model."""
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(String(255), nullable=False, default="default_user", index=True)
    conversation_type = Column(String(50), default="voice", index=True)  # voice, text, wake_word, unlock
    user_input = Column(Text, nullable=True)
    aria_response = Column(Text, nullable=True)
    context_data = Column(JSON, default=dict)
    response_time_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    session = relationship("Session", back_populates="conversations")

    def __repr__(self):
        return f"<Conversation(id={self.id}, type={self.conversation_type}, timestamp={self.timestamp})>"


class UserContext(Base):
    """User context and preferences model."""
    __tablename__ = "user_context"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, default="default_user", index=True)
    context_key = Column(String(255), nullable=False, index=True)
    context_value = Column(JSON, nullable=False)
    context_type = Column(String(50), default="preference", index=True)  # preference, memory, pattern, learned
    importance_score = Column(Integer, default=1, index=True)  # 1-10 scale
    last_accessed = Column(DateTime(timezone=True), default=func.now())
    access_count = Column(Integer, default=1)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<UserContext(user_id={self.user_id}, key={self.context_key}, type={self.context_type})>"


class SystemEvent(Base):
    """System events model (unlock, wake_word, etc.)."""
    __tablename__ = "system_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(String(255), nullable=False, default="default_user", index=True)
    event_type = Column(String(50), nullable=False, index=True)  # unlock, wake_word, boot, shutdown
    event_data = Column(JSON, default=dict)
    response_generated = Column(Boolean, default=False)
    response_text = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    session = relationship("Session", back_populates="system_events")

    def __repr__(self):
        return f"<SystemEvent(id={self.id}, type={self.event_type}, timestamp={self.timestamp})>"


class InteractionPattern(Base):
    """Voice interaction patterns model."""
    __tablename__ = "interaction_patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, default="default_user", index=True)
    pattern_type = Column(String(50), nullable=False, index=True)  # daily_routine, common_questions, preferences
    pattern_data = Column(JSON, nullable=False)
    frequency = Column(Integer, default=1)
    last_occurrence = Column(DateTime(timezone=True), default=func.now())
    confidence_score = Column(Float, default=0.5)  # 0.0 to 1.0
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<InteractionPattern(user_id={self.user_id}, type={self.pattern_type}, frequency={self.frequency})>"


class BibleQuery(Base):
    """Bible query history model."""
    __tablename__ = "bible_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, default="default_user", index=True)
    query_text = Column(Text, nullable=False)
    query_type = Column(String(50), default="question", index=True)  # question, topic, verse_lookup, daily
    translation = Column(String(10), default="BSB", index=True)
    results_data = Column(JSON, default=dict)
    ai_response = Column(Text, nullable=True)
    sources_count = Column(Integer, default=0)
    response_time_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=True)
    timestamp = Column(DateTime(timezone=True), default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), default=func.now())

    def __repr__(self):
        return f"<BibleQuery(id={self.id}, type={self.query_type}, query='{self.query_text[:50]}...')>"


class BibleStudySession(Base):
    """Bible study session model."""
    __tablename__ = "bible_study_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, default="default_user", index=True)
    session_type = Column(String(50), default="general", index=True)  # general, topic_study, daily_reading
    topic = Column(String(255), nullable=True, index=True)
    verses_studied = Column(JSON, default=list)  # List of verse references
    queries_count = Column(Integer, default=0)
    duration_minutes = Column(Integer, nullable=True)
    session_start = Column(DateTime(timezone=True), default=func.now())
    session_end = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<BibleStudySession(id={self.id}, type={self.session_type}, topic={self.topic})>"


class UserBiblePreferences(Base):
    """User Bible preferences and reading progress."""
    __tablename__ = "user_bible_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, default="default_user", index=True)
    preferred_translation = Column(String(10), default="BSB")
    favorite_verses = Column(JSON, default=list)  # List of verse references
    reading_plan = Column(JSON, default=dict)  # Reading plan configuration
    reading_progress = Column(JSON, default=dict)  # Progress tracking
    study_topics = Column(JSON, default=list)  # Preferred study topics
    daily_verse_enabled = Column(Boolean, default=True)
    commentary_enabled = Column(Boolean, default=True)
    difficulty_level = Column(String(20), default="intermediate")  # beginner, intermediate, advanced
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<UserBiblePreferences(user_id={self.user_id}, translation={self.preferred_translation})>"


# Add unique constraint for user_context
from sqlalchemy import UniqueConstraint
UserContext.__table_args__ = (
    UniqueConstraint('user_id', 'context_key', name='uq_user_context_user_key'),
)

# Add unique constraint for user_bible_preferences
UserBiblePreferences.__table_args__ = (
    UniqueConstraint('user_id', name='uq_user_bible_preferences_user'),
)
