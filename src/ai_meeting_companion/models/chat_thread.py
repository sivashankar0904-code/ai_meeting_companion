from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime

from ai_meeting_companion.models.base import Base, timestamp, uuid_pk


class ChatThread(Base):
    __tablename__ = "chat_thread"
    __table_args__ = (Index("idx_chat_thread_created", "created_at", postgresql_ops={"created_at": "DESC"}),)

    id: Mapped[UUID] = uuid_pk()
    title: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")  # active | ended
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    summary: Mapped[str | None] = mapped_column(Text)
    # "metadata" is reserved on declarative classes, so the attribute is `meta`.
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = timestamp()
    updated_at: Mapped[datetime] = timestamp()
