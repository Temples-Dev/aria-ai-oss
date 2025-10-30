"""
SQLAlchemy models for ARIA database.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
    session_data = Column(JSONB, default=dict)
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
    context_data = Column(JSONB, default=dict)
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
    context_value = Column(JSONB, nullable=False)
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
    event_data = Column(JSONB, default=dict)
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
    pattern_data = Column(JSONB, nullable=False)
    frequency = Column(Integer, default=1)
    last_occurrence = Column(DateTime(timezone=True), default=func.now())
    confidence_score = Column(Float, default=0.5)  # 0.0 to 1.0
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<InteractionPattern(user_id={self.user_id}, type={self.pattern_type}, frequency={self.frequency})>"


# Add unique constraint for user_context
from sqlalchemy import UniqueConstraint
UserContext.__table_args__ = (
    UniqueConstraint('user_id', 'context_key', name='uq_user_context_user_key'),
)
