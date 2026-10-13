from __future__ import annotations

import logging
from uuid import UUID

from ai_meeting_companion.core.agent import BaseAgent
from ai_meeting_companion.core.bus import Bus
from ai_meeting_companion.core.events import (
    ERROR,
    LLM_RESPONSE,
    SCREEN_TEXT,
    STATUS,
    SUGGEST_REQUEST,
    TRANSCRIPT,
    USER_MESSAGE,
    Event,
)
from ai_meeting_companion.records import NewMessage
from ai_meeting_companion.session.store import SessionStore

log = logging.getLogger(__name__)

_SOURCE = {TRANSCRIPT: "audio", SCREEN_TEXT: "screen", USER_MESSAGE: "manual"}


def event_to_message(event: Event) -> NewMessage:
    p = event.payload
    if event.kind == LLM_RESPONSE:
        return NewMessage(
            id=event.id,
            role="assistant",
            source="agent",
            agent=p.get("agent") or event.source,
            message_content=event.text,
            parent_message_id=event.parent_id,
            model=p.get("model"),
            input_tokens=p.get("input_tokens"),
            output_tokens=p.get("output_tokens"),
            latency_ms=p.get("latency_ms"),
            metadata={"roles": p["roles"]} if p.get("roles") else {},
            created_at=event.ts,
        )
    if event.kind == ERROR:
        return NewMessage(
            id=event.id, role="system", source="agent", agent=p.get("agent") or event.source,
            message_content=event.text, metadata={"error": True}, created_at=event.ts,
        )
    metadata = {"channel": p["channel"]} if p.get("channel") else {}
    return NewMessage(
        id=event.id,
        role="user",
        source=_SOURCE.get(event.kind, event.source),
        message_content=event.text,
        speaker=p.get("speaker"),
        metadata=metadata,
        created_at=event.ts,
    )


class SessionLogger(BaseAgent):
    """Subscribes to every event and writes it to the store."""

    name = "session_logger"

    def __init__(self, bus: Bus, store: SessionStore, thread_id: UUID) -> None:
        super().__init__(bus)
        self.store = store
        self.thread_id = thread_id

    def start(self) -> None:
        self._sub = self.bus.subscribe(None)
        super().start()

    def handle(self, event: Event) -> None:
        if event.kind in (STATUS, SUGGEST_REQUEST):
            return
        try:
            self.store.add_message(self.thread_id, event_to_message(event))
        except Exception:
            # Never publish an error event from here: the logger would receive and re-log it forever.
            log.exception("failed to log %s event %s", event.kind, event.id)

    def drain(self) -> None:
        """Write whatever is still queued; called after the other agents have stopped."""
        assert self._sub is not None
        while (event := self._sub.get(timeout=0)) is not None:
            self.handle(event)
