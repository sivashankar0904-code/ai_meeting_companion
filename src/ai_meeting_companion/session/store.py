from __future__ import annotations

import threading
from dataclasses import asdict, replace
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy import create_engine, desc, func, select, text, update
from sqlalchemy.orm import sessionmaker

from ai_meeting_companion.config import DbSettings
from ai_meeting_companion.models import Base, ChatMessage, ChatThread
from ai_meeting_companion.records import Message, NewMessage, Thread, utcnow


class SessionStore(Protocol):
    def create_thread(self, title: str | None = None, metadata: dict[str, Any] | None = None) -> Thread: ...
    def add_message(self, thread_id: UUID, message: NewMessage) -> int: ...
    def end_thread(self, thread_id: UUID, summary: str | None = None) -> None: ...
    def get_thread(self, thread_id: UUID) -> Thread | None: ...
    def list_threads(self, limit: int = 50) -> list[Thread]: ...
    def get_messages(self, thread_id: UUID) -> list[Message]: ...
    def close(self) -> None: ...


class InMemorySessionStore:
    """Same contract as SqlAlchemySessionStore; used by tests."""

    def __init__(self) -> None:
        self._threads: dict[UUID, Thread] = {}
        self._messages: dict[UUID, list[Message]] = {}
        self._lock = threading.Lock()

    def create_thread(self, title: str | None = None, metadata: dict[str, Any] | None = None) -> Thread:
        now = utcnow()
        thread = Thread(id=uuid4(), title=title, metadata=dict(metadata or {}), created_at=now, updated_at=now)
        with self._lock:
            self._threads[thread.id] = thread
            self._messages[thread.id] = []
        return thread

    def add_message(self, thread_id: UUID, message: NewMessage) -> int:
        with self._lock:
            thread = self._threads[thread_id]
            seq = thread.message_count + 1
            self._threads[thread_id] = replace(thread, message_count=seq, updated_at=utcnow())
            self._messages[thread_id].append(Message(**asdict(message), thread_id=thread_id, seq=seq))
            return seq

    def end_thread(self, thread_id: UUID, summary: str | None = None) -> None:
        with self._lock:
            now = utcnow()
            self._threads[thread_id] = replace(
                self._threads[thread_id], status="ended", summary=summary, ended_at=now, updated_at=now
            )

    def get_thread(self, thread_id: UUID) -> Thread | None:
        return self._threads.get(thread_id)

    def list_threads(self, limit: int = 50) -> list[Thread]:
        return sorted(self._threads.values(), key=lambda t: t.created_at, reverse=True)[:limit]

    def get_messages(self, thread_id: UUID) -> list[Message]:
        with self._lock:
            return list(self._messages.get(thread_id, []))

    def close(self) -> None:
        pass


def _to_thread(row: ChatThread) -> Thread:
    return Thread(
        id=row.id, title=row.title, status=row.status, message_count=row.message_count,
        summary=row.summary, metadata=row.meta, created_at=row.created_at,
        updated_at=row.updated_at, ended_at=row.ended_at,
    )


def _to_message(row: ChatMessage) -> Message:
    return Message(
        id=row.id, thread_id=row.thread_id, seq=row.seq, parent_message_id=row.parent_message_id,
        role=row.role, source=row.source, agent=row.agent, speaker=row.speaker,
        message_content=row.message_content, model=row.model, input_tokens=row.input_tokens,
        output_tokens=row.output_tokens, latency_ms=row.latency_ms, metadata=row.meta,
        created_at=row.created_at,
    )


class SqlAlchemySessionStore:
    """PostgreSQL store. Rows go through SQLAlchemy ORM models; callers only see the dataclasses in ``records``."""

    def __init__(self, db: DbSettings, schema: str | None = None) -> None:
        self._schema = schema
        connect_args: dict[str, Any] = {}
        if schema:
            # Throwaway schema for tests: create it, then pin search_path for every connection.
            bootstrap = create_engine(db.url(), isolation_level="AUTOCOMMIT")
            with bootstrap.connect() as conn:
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
            bootstrap.dispose()
            connect_args["options"] = f"-c search_path={schema}"
        self._engine = create_engine(
            db.url(),
            pool_size=db.pool_min,
            max_overflow=max(db.pool_max - db.pool_min, 0),
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        self._sessions = sessionmaker(self._engine, expire_on_commit=False)
        Base.metadata.create_all(self._engine)

    def drop_schema(self) -> None:
        """Test helper: remove the throwaway schema this store was created with."""
        if not self._schema:
            raise RuntimeError("refusing to drop the default schema")
        self._engine.dispose()
        with self._engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{self._schema}" CASCADE'))

    def create_thread(self, title: str | None = None, metadata: dict[str, Any] | None = None) -> Thread:
        with self._sessions.begin() as s:
            row = ChatThread(title=title, meta=metadata or {})
            s.add(row)
            s.flush()
            s.refresh(row)
            return _to_thread(row)

    def add_message(self, thread_id: UUID, message: NewMessage) -> int:
        # Bumping message_count takes the thread row lock, so seq is unique per thread.
        with self._sessions.begin() as s:
            seq = s.execute(
                update(ChatThread)
                .where(ChatThread.id == thread_id)
                .values(message_count=ChatThread.message_count + 1, updated_at=func.now())
                .returning(ChatThread.message_count)
            ).scalar_one_or_none()
            if seq is None:
                raise KeyError(f"unknown thread {thread_id}")
            s.add(
                ChatMessage(
                    id=message.id, thread_id=thread_id, seq=seq,
                    parent_message_id=message.parent_message_id, role=message.role,
                    source=message.source, agent=message.agent, speaker=message.speaker,
                    message_content=message.message_content, model=message.model,
                    input_tokens=message.input_tokens, output_tokens=message.output_tokens,
                    latency_ms=message.latency_ms, meta=message.metadata, created_at=message.created_at,
                )
            )
            return seq

    def end_thread(self, thread_id: UUID, summary: str | None = None) -> None:
        with self._sessions.begin() as s:
            s.execute(
                update(ChatThread)
                .where(ChatThread.id == thread_id)
                .values(status="ended", summary=summary, ended_at=func.now(), updated_at=func.now())
            )

    def get_thread(self, thread_id: UUID) -> Thread | None:
        with self._sessions() as s:
            row = s.get(ChatThread, thread_id)
            return _to_thread(row) if row else None

    def list_threads(self, limit: int = 50) -> list[Thread]:
        with self._sessions() as s:
            rows = s.scalars(select(ChatThread).order_by(desc(ChatThread.created_at)).limit(limit)).all()
            return [_to_thread(r) for r in rows]

    def get_messages(self, thread_id: UUID) -> list[Message]:
        with self._sessions() as s:
            rows = s.scalars(select(ChatMessage).where(ChatMessage.thread_id == thread_id).order_by(ChatMessage.seq)).all()
            return [_to_message(r) for r in rows]

    def close(self) -> None:
        self._engine.dispose()
