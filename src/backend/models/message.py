import enum
from sqlalchemy import Column, String, ForeignKey, Enum, Text, Integer, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.backend.models.base import BaseModel


class MessageRole(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL_CALL = "tool_call"
    TOOL_OUTPUT = "tool_output"


class Message(BaseModel):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conv_created", "conversation_id", "created_at"),
        Index("ix_messages_conv_sequence", "conversation_id", "sequence"),
    )

    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(
        Enum(MessageRole, name="messagerole", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    content = Column(Text, nullable=True)  # Text content for user/assistant messages
    sequence = Column(Integer, nullable=False)  # Ordering within a conversation

    # For tool_call messages: stores {name, arguments, call_id}
    # For tool_output messages: stores {call_id, output}
    meta = Column(JSONB, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")
