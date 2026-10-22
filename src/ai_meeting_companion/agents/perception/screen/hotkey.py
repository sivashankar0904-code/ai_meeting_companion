from __future__ import annotations

from typing import Callable, Protocol


class HotkeyListener(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...


def make_hotkey_listener(hotkey: str, callback: Callable[[], None]) -> HotkeyListener:
    from ai_meeting_companion.hotkeys import GlobalHotkeys

    return GlobalHotkeys({hotkey: callback})
