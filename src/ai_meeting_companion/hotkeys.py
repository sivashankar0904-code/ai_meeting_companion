"""Global hotkeys that are consumed, so the meeting app never sees them.

pynput's ``GlobalHotKeys`` only listens: the keystroke still reaches the focused window, and
Ctrl+Shift+H is "leave meeting" in Teams (Ctrl+Shift+A / S accept calls). This listener filters
the low-level keyboard hook and swallows the key that completes a hotkey, plus its release.
Modifiers still pass through; on their own they do nothing.
"""

from __future__ import annotations

import ctypes
import threading
from typing import Callable, Mapping

_MODIFIERS = {"ctrl": "ctrl", "control": "ctrl", "shift": "shift", "alt": "alt", "cmd": "win", "win": "win"}
_MODIFIER_VKS = {"ctrl": (0x11,), "shift": (0x10,), "alt": (0x12,), "win": (0x5B, 0x5C)}

_WM_KEYDOWN = 0x0100
_WM_SYSKEYDOWN = 0x0104
_LLKHF_INJECTED = 0x10


def parse_hotkey(spec: str) -> tuple[frozenset[str], int]:
    """``"<ctrl>+<shift>+h"`` -> ({"ctrl", "shift"}, virtual-key code of H)."""
    mods: set[str] = set()
    vk: int | None = None
    for part in spec.lower().split("+"):
        part = part.strip()
        name = part[1:-1] if len(part) > 2 and part[0] == "<" and part[-1] == ">" else None
        if name in _MODIFIERS:
            mods.add(_MODIFIERS[name])
            continue
        if vk is not None:
            raise ValueError(f"hotkey {spec!r} has more than one non-modifier key")
        if name is not None:
            vk = _named_vk(name, spec)
        elif len(part) == 1:
            vk = _char_vk(part, spec)
        else:
            raise ValueError(f"cannot parse hotkey {spec!r}")
    if vk is None:
        raise ValueError(f"hotkey {spec!r} has no key besides modifiers")
    return frozenset(mods), vk


def _named_vk(name: str, spec: str) -> int:
    if name.isdigit():
        return int(name)
    from pynput.keyboard import Key

    try:
        return Key[name].value.vk
    except (KeyError, AttributeError):
        raise ValueError(f"unknown key <{name}> in hotkey {spec!r}") from None


def _char_vk(char: str, spec: str) -> int:
    if char.isascii() and char.isalnum():
        return ord(char.upper())
    code = ctypes.windll.user32.VkKeyScanW(ord(char))
    if code == -1:
        raise ValueError(f"key {char!r} in hotkey {spec!r} is not on this keyboard layout")
    return code & 0xFF


def _held_modifiers() -> frozenset[str]:
    state = ctypes.windll.user32.GetAsyncKeyState
    return frozenset(mod for mod, vks in _MODIFIER_VKS.items() if any(state(vk) & 0x8000 for vk in vks))


class GlobalHotkeys:
    """Calls ``bindings[spec]`` when that combination is pressed and swallows the keystroke.

    Matching is exact (Ctrl+Shift+Alt+H does not fire Ctrl+Shift+H). Callbacks run on a short-lived
    thread so the keyboard hook returns quickly; they should only signal (Qt signal, threading.Event)."""

    def __init__(self, bindings: Mapping[str, Callable[[], None]]) -> None:
        self._bindings = {parse_hotkey(spec): callback for spec, callback in bindings.items()}
        self._swallowing: set[int] = set()  # hotkey keys still held down: their repeats and release are eaten too
        self._listener = None

    def match(self, vk: int, modifiers: frozenset[str]) -> Callable[[], None] | None:
        return self._bindings.get((modifiers, vk))

    def start(self) -> None:
        from pynput import keyboard

        self._listener = keyboard.Listener(win32_event_filter=self._filter)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()

    def _filter(self, msg: int, data) -> bool:
        """Runs inside the low-level keyboard hook. Returns False: pynput callbacks are not used.

        Any error other than the suppression signal would stop pynput's listener (and every
        hotkey with it), so the decision is made under a broad except."""
        try:
            swallow = self._decide(msg, data.vkCode, bool(data.flags & _LLKHF_INJECTED))
        except Exception:
            swallow = False
        if swallow:
            self._listener.suppress_event()
        return False

    def _decide(self, msg: int, vk: int, injected: bool) -> bool:
        """True when this key event belongs to a hotkey and must not reach other apps."""
        if injected:
            return False
        if msg in (_WM_KEYDOWN, _WM_SYSKEYDOWN):
            if vk in self._swallowing:  # auto-repeat while held
                return True
            callback = self.match(vk, _held_modifiers())
            if callback is None:
                return False
            self._swallowing.add(vk)
            threading.Thread(target=callback, daemon=True).start()
            return True
        if vk in self._swallowing:  # release of a hotkey key
            self._swallowing.discard(vk)
            return True
        return False
