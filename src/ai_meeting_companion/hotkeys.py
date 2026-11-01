"""Global hotkeys that are consumed, so the meeting app never sees them.

pynput's ``GlobalHotKeys`` only listens: the keystroke still reaches the focused window, and
Ctrl+Shift+H is "leave meeting" in Teams (Ctrl+Shift+A / S accept calls). This listener filters
the low-level keyboard hook and swallows the key that completes a hotkey, plus its release.
Modifiers still pass through; on their own they do nothing.
"""

from __future__ import annotations

import sys
import threading
from typing import Callable, Mapping

_MODIFIERS = {"ctrl": "ctrl", "control": "ctrl", "shift": "shift", "alt": "alt", "cmd": "win", "win": "win"}
_MODIFIER_VKS = {"ctrl": (0x11,), "shift": (0x10,), "alt": (0x12,), "win": (0x5B, 0x5C)}
_MAC = sys.platform == "darwin"

# macOS virtual key codes (ANSI layout); the hook there reports these instead of Windows VKs.
_MAC_KEYCODES = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11, "q": 12,
    "w": 13, "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23,
    "9": 25, "7": 26, "8": 28, "0": 29, "o": 31, "u": 32, "i": 34, "p": 35, "l": 37, "j": 38, "k": 40,
    "n": 45, "m": 46, "=": 24, "-": 27, "]": 30, "[": 33, "'": 39, ";": 41, "\\": 42, ",": 43, "/": 44,
    ".": 47, "`": 50,
}
_MAC_NAMED = {"enter": 36, "tab": 48, "space": 49, "backspace": 51, "esc": 53,
              "left": 123, "right": 124, "down": 125, "up": 126}
# Quartz CGEventFlags masks
_MAC_FLAGS = {"shift": 0x20000, "ctrl": 0x40000, "alt": 0x80000, "win": 0x100000}
_MAC_KEYDOWN, _MAC_KEYUP = 10, 11

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
    if _MAC:
        if name in _MAC_NAMED:
            return _MAC_NAMED[name]
        raise ValueError(f"unknown key <{name}> in hotkey {spec!r}")
    if name.isdigit():
        return int(name)
    from pynput.keyboard import Key

    try:
        return Key[name].value.vk
    except (KeyError, AttributeError):
        raise ValueError(f"unknown key <{name}> in hotkey {spec!r}") from None


def _char_vk(char: str, spec: str) -> int:
    if _MAC:
        try:
            return _MAC_KEYCODES[char.lower()]
        except KeyError:
            raise ValueError(f"key {char!r} in hotkey {spec!r} is not supported on macOS") from None
    import ctypes

    if char.isascii() and char.isalnum():
        return ord(char.upper())
    code = ctypes.windll.user32.VkKeyScanW(ord(char))
    if code == -1:
        raise ValueError(f"key {char!r} in hotkey {spec!r} is not on this keyboard layout")
    return code & 0xFF


def _held_modifiers() -> frozenset[str]:
    import ctypes

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

        if _MAC:  # needs Accessibility / Input Monitoring permission for the terminal or app
            self._listener = keyboard.Listener(darwin_intercept=self._intercept_mac)
        else:
            self._listener = keyboard.Listener(win32_event_filter=self._filter)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()

    def _intercept_mac(self, event_type, event):
        """Runs inside the Quartz event tap. Returns None to swallow the event, else the event."""
        try:
            import Quartz

            if event_type not in (_MAC_KEYDOWN, _MAC_KEYUP):
                return event
            code = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            flags = Quartz.CGEventGetFlags(event)
            mods = frozenset(m for m, mask in _MAC_FLAGS.items() if flags & mask)
            injected = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGEventSourceUnixProcessID) != 0
            swallow = self._decide_key(event_type == _MAC_KEYDOWN, code, mods, injected)
        except Exception:
            swallow = False
        return None if swallow else event

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
        return self._decide_key(msg in (_WM_KEYDOWN, _WM_SYSKEYDOWN), vk, None, injected)

    def _decide_key(self, down: bool, vk: int, modifiers: frozenset[str] | None, injected: bool) -> bool:
        if injected:
            return False
        if down:
            if vk in self._swallowing:  # auto-repeat while held
                return True
            callback = self.match(vk, _held_modifiers() if modifiers is None else modifiers)
            if callback is None:
                return False
            self._swallowing.add(vk)
            threading.Thread(target=callback, daemon=True).start()
            return True
        if vk in self._swallowing:  # release of a hotkey key
            self._swallowing.discard(vk)
            return True
        return False
