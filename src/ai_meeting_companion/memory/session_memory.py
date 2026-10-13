from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ai_meeting_companion.core.events import LLM_RESPONSE, SCREEN_TEXT, TRANSCRIPT, USER_MESSAGE, Event

MAX_ENTRIES = 400

# How much of each entry is shown. The newest screen capture and each agent's newest reply are the
# ones people usually refer to ("this problem", "your last answer"), so they get more room.
CAP_LATEST_SCREEN = 3000
CAP_OLDER_SCREEN = 400
CAP_LATEST_REPLY = 1500
CAP_OLDER_REPLY = 300
CAP_SPEECH = 500


@dataclass(frozen=True)
class Entry:
    id: UUID
    ts: datetime
    kind: str
    who: str  # channel for speech, agent name for replies
    text: str


def _shorten(text: str, limit: int) -> str:
    text = " ".join(text.split()) if limit <= CAP_SPEECH else text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


class SessionMemory:
    """One timeline shared by every agent: what was heard, what was on screen, what the user typed,
    and what each assistant answered.

    Without it each agent only sees its own inputs, so a spoken "explain this problem" has no idea a
    screenshot was just taken. It is fed by a tap on the bus (``bus.add_tap(memory.record)``), so an
    event is always recorded before any agent reacts to it.
    """

    def __init__(self, max_entries: int = MAX_ENTRIES) -> None:
        self._entries: deque[Entry] = deque(maxlen=max_entries)
        self._lock = threading.Lock()

    def record(self, event: Event) -> None:
        text = event.text.strip()
        if not text or event.kind not in (TRANSCRIPT, SCREEN_TEXT, USER_MESSAGE, LLM_RESPONSE):
            return
        who = event.payload.get("channel") or event.payload.get("agent") or event.source
        with self._lock:
            self._entries.append(Entry(event.id, event.ts, event.kind, str(who), text))

    def __len__(self) -> int:
        return len(self._entries)

    def render(self, exclude: frozenset[UUID] | set[UUID] = frozenset(), max_chars: int = 8000) -> str:
        """The timeline as text, oldest first, newest entries kept when the budget is short.

        ``exclude`` drops entries the caller is about to send as its own new input."""
        with self._lock:
            entries = [e for e in self._entries if e.id not in exclude]
        latest_screen = next((e.id for e in reversed(entries) if e.kind == SCREEN_TEXT), None)
        latest_reply: dict[str, UUID] = {}
        for e in reversed(entries):
            if e.kind == LLM_RESPONSE:
                latest_reply.setdefault(e.who, e.id)

        lines: list[str] = []
        used = 0
        for e in reversed(entries):
            if e.kind == SCREEN_TEXT:
                line = f"SCREEN (text read from the user's screen): {_shorten(e.text, CAP_LATEST_SCREEN if e.id == latest_screen else CAP_OLDER_SCREEN)}"
            elif e.kind == LLM_RESPONSE:
                cap = CAP_LATEST_REPLY if latest_reply.get(e.who) == e.id else CAP_OLDER_REPLY
                line = f"{e.who} replied: {_shorten(e.text, cap)}"
            elif e.kind == USER_MESSAGE:
                line = f"user typed: {_shorten(e.text, CAP_SPEECH)}"
            else:
                line = f"heard ({e.who}): {_shorten(e.text, CAP_SPEECH)}"
            line = f"[{e.ts.astimezone():%H:%M:%S}] {line}"
            if lines and used + len(line) > max_chars:
                break
            lines.append(line)
            used += len(line) + 1
        return "\n".join(reversed(lines))
