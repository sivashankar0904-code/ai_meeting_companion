from __future__ import annotations

from uuid import UUID

from ai_meeting_companion.session.store import SessionStore


def export_markdown(store: SessionStore, thread_id: UUID) -> str:
    thread = store.get_thread(thread_id)
    if thread is None:
        raise KeyError(f"unknown session {thread_id}")

    lines = [
        f"# {thread.title or 'Meeting session'}",
        "",
        f"- Session: `{thread.id}`",
        f"- Started: {thread.created_at:%Y-%m-%d %H:%M:%S %Z}",
        f"- Status: {thread.status}",
        f"- Messages: {thread.message_count}",
        "",
    ]
    if thread.summary:
        lines += ["## Summary", "", thread.summary, ""]
    lines += ["## Transcript", ""]
    for m in store.get_messages(thread_id):
        who = m.agent if m.role == "assistant" else m.source
        if m.role == "system":
            who = f"error:{m.agent}"
        elif m.speaker:
            who = f"{who} ({m.speaker})"
        lines += [f"**[{m.created_at:%H:%M:%S}] {who}**", "", m.message_content, ""]
    return "\n".join(lines)
