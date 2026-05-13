import enum
from sqlalchemy import Column, String, ForeignKey, Enum, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from src.backend.models.base import BaseModel


class ConversationType(enum.Enum):
    CURRICULUM = "curriculum"
    TEACHER = "teacher"
    QUIZ = "quiz"


class Conversation(BaseModel):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_user_chapter_type", "user_id", "chapter_id", "type"),
    )

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Polymorphic link: either topic_id or chapter_id will be set
    topic_id = Column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=True
    )
    chapter_id = Column(
        UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=True
    )
    type = Column(
        Enum(ConversationType, name="conversationtype", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    title = Column(String, nullable=True)  # Optional summary/title for sidebar display

    # Relationships
    user = relationship("User", backref="conversations")
    topic = relationship("Topic", backref="conversations")
    chapter = relationship("Chapter", backref="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="selectin",
    )
