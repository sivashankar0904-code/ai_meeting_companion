from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from ai_meeting_companion.models.base import Base, timestamp, uuid_pk


class ChatMessage(Base):
    __tablename__ = "chat_message"
    __table_args__ = (
        UniqueConstraint("thread_id", "seq"),
        Index("idx_chat_message_thread_seq", "thread_id", "seq"),
    )

    id: Mapped[UUID] = uuid_pk()
    thread_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("chat_thread.id", ondelete="CASCADE"), nullable=False
    )
    parent_message_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("chat_message.id"))
    seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)  # user | assistant | system
    source: Mapped[str] = mapped_column(Text, nullable=False)  # audio | screen | manual | agent
    agent: Mapped[str | None] = mapped_column(Text)  # conversor | screen_analyzer | chat
    speaker: Mapped[str | None] = mapped_column(Text)  # interviewer | interviewee | unknown
    message_content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(Text)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = timestamp()
    updated_at: Mapped[datetime] = timestamp()
