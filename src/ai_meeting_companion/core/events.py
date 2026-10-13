from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

TRANSCRIPT = "transcript"
SCREEN_TEXT = "screen_text"
USER_MESSAGE = "user_message"
LLM_RESPONSE = "llm_response"
ERROR = "error"
STATUS = "status"  # transient progress text for the UI; never logged
SUGGEST_REQUEST = "suggest_request"  # user asks the Conversor for a suggestion now; never logged

# Payload conventions (all carry "text"):
#   transcript:    {"text", "channel"?}            channel: "loopback" | "mic"
#   screen_text:   {"text"}
#   user_message:  {"text"}
#   llm_response:  {"text", "agent", "model", "input_tokens", "output_tokens", "latency_ms", "roles"?}
#   error:         {"text", "agent"?}
#   status:        {"text"}
#   suggest_request: {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Event:
    kind: str
    source: str
    payload: dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    parent_id: UUID | None = None
    ts: datetime = field(default_factory=_now)

    @property
    def text(self) -> str:
        return str(self.payload.get("text", ""))
