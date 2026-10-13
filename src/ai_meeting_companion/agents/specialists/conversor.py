from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from ai_meeting_companion.agents.specialists.base import SpecialistAgent
from ai_meeting_companion.core.bus import Bus
from ai_meeting_companion.core.events import STATUS, SUGGEST_REQUEST, TRANSCRIPT, Event
from ai_meeting_companion.llm.chains import build_chain
from ai_meeting_companion.memory.session_memory import SessionMemory
from ai_meeting_companion.prompts.loader import build_system_prompt

_ROLES_LINE = re.compile(r"^\s*ROLES:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_PAIR = re.compile(r"(interviewer|interviewee)\s*=\s*([^;]+)", re.IGNORECASE)

MAX_PENDING_CHARS = 8000  # oldest lines are dropped beyond this, so one request never gets huge

# (channel, text, event id, time heard)
_Line = tuple[str | None, str, UUID, datetime]


def parse_roles(text: str) -> dict[str, str]:
    """Extract {"interviewer": label, "interviewee": label} from the model's ROLES line."""
    m = _ROLES_LINE.search(text)
    if not m:
        return {}
    return {role.lower(): label.strip() for role, label in _PAIR.findall(m.group(1))}


def strip_roles(text: str) -> str:
    return _ROLES_LINE.sub("", text, count=1).strip()


class Conversor(SpecialistAgent):
    """Collects the transcript for free and calls the model only when asked.

    Transcript chunks are just buffered. A ``suggest_request`` event (hotkey or overlay button)
    sends what was heard since the last request, together with the shared session timeline
    (screen captures, earlier answers), and publishes the suggested answer, so tokens are spent
    only when the user wants a suggestion.
    """

    def __init__(
        self,
        bus: Bus,
        model,
        model_name: str,
        *,
        background: str = "",
        memory: SessionMemory | None = None,
        memory_chars: int = 8000,
    ) -> None:
        super().__init__(
            bus,
            name="conversor",
            chain=build_chain(model, build_system_prompt("conversor", background)),
            model_name=model_name,
            trigger_kind=TRANSCRIPT,
            memory=memory,
            memory_chars=memory_chars,
        )
        self.kinds = self.kinds | {SUGGEST_REQUEST}
        self._pending: list[_Line] = []
        self.roles: dict[str, str] = {}

    def handle(self, event: Event) -> None:
        if event.kind == SUGGEST_REQUEST:
            self.suggest()
        else:
            super().handle(event)

    def on_trigger(self, event: Event) -> None:
        """A transcript chunk: remember it, nothing more."""
        text = event.text.strip()
        if not text:
            return
        self._pending.append((event.payload.get("channel"), text, event.id, event.ts))
        # +25 covers the '[HH:MM:SS][channel] ' prefix each line gets when sent
        while len(self._pending) > 1 and sum(len(line[1]) + 25 for line in self._pending) > MAX_PENDING_CHARS:
            self._pending.pop(0)

    def _status(self, text: str) -> None:
        self.publish(Event(kind=STATUS, source=self.name, payload={"text": text}))

    def suggest(self) -> None:
        if not self._pending:
            self._status("Conversor: nothing new heard since the last suggestion, nothing sent")
            return
        pending, self._pending = self._pending, []
        lines = [
            f"[{ts.astimezone():%H:%M:%S}]" + (f"[{ch}] " if ch else " ") + text for ch, text, _id, ts in pending
        ]
        known = "; ".join(f"{k}={v}" for k, v in self.roles.items()) or "none yet"
        prompt = (
            f"Known roles: {known}\n"
            "The user asked for a suggestion now. Newly heard since the last suggestion "
            "(answer the most recent question; check 'Session so far' for what it refers to):\n" + "\n".join(lines)
        )
        self._status(f"Conversor: sending {len(lines)} transcript line(s) to the model...")
        try:
            self.ask(prompt, parent_id=pending[-1][2], exclude=[line[2] for line in pending])
        except Exception:
            self._pending = pending + self._pending  # nothing was answered; keep it for the next try
            raise

    def finalize(self, answer: str) -> tuple[str, dict] | None:
        roles = parse_roles(answer)
        if roles:
            self.roles = {**self.roles, **roles}
        body = strip_roles(answer)
        if not body or body.upper().startswith("NO_QUESTION"):
            # Say so, otherwise "nothing to answer" looks exactly like "not working".
            known = "; ".join(f"{k}={v}" for k, v in self.roles.items()) or "roles not clear yet"
            self._status(f"Conversor: no interviewer question to answer yet ({known})")
            return None
        return body, {"roles": dict(self.roles)}
