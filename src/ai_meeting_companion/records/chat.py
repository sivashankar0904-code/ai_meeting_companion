from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, kw_only=True)
class NewMessage:
    """A message about to be stored (the store assigns thread_id and seq)."""

    role: str  # user | assistant | system
    source: str  # audio | screen | manual | agent
    message_content: str
    id: UUID = field(default_factory=uuid4)
    parent_message_id: UUID | None = None
    agent: str | None = None
    speaker: str | None = None
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True, kw_only=True)
class Message(NewMessage):
    thread_id: UUID
    seq: int


@dataclass(frozen=True, kw_only=True)
class Thread:
    id: UUID
    created_at: datetime
    updated_at: datetime
    title: str | None = None
    status: str = "active"
    message_count: int = 0
    summary: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    ended_at: datetime | None = None
