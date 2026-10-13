from __future__ import annotations

from typing import Callable, Mapping


def start_hotkeys(bindings: Mapping[str, Callable[[], None]]):
    """Register global hotkeys ({"<ctrl>+<shift>+h": callback}); returns the running listener.

    Callbacks run on pynput's thread, so they must only emit Qt signals."""
    from pynput import keyboard

    listener = keyboard.GlobalHotKeys(dict(bindings))
    listener.start()
    return listener
