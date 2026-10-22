from __future__ import annotations

from typing import Callable, Mapping

from ai_meeting_companion.hotkeys import GlobalHotkeys


def start_hotkeys(bindings: Mapping[str, Callable[[], None]]) -> GlobalHotkeys:
    """Register global hotkeys ({"<ctrl>+<shift>+h": callback}); returns the running listener.

    The keystrokes are swallowed so Teams/Zoom never see them. Callbacks run on a worker
    thread, so they must only emit Qt signals."""
    listener = GlobalHotkeys(bindings)
    listener.start()
    return listener
