from __future__ import annotations

import sys

WDA_NONE = 0x00
WDA_MONITOR = 0x01  # window shows as a black box in captures (older Windows)
WDA_EXCLUDEFROMCAPTURE = 0x11  # window is omitted from captures (Windows 10 2004+)


def _user32():
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
    user32.GetWindowDisplayAffinity.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowDisplayAffinity.restype = wintypes.BOOL
    return user32


def set_capture_excluded(hwnd: int, excluded: bool = True) -> bool:
    """Hide the window from screen capture / screen sharing. Returns True if Windows accepted it."""
    if sys.platform != "win32" or not hwnd:
        return False
    user32 = _user32()
    if not excluded:
        return bool(user32.SetWindowDisplayAffinity(hwnd, WDA_NONE))
    return bool(user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE))


def display_affinity(hwnd: int) -> int | None:
    """The window's current WDA_* value, or None when unavailable."""
    if sys.platform != "win32" or not hwnd:
        return None
    from ctypes import wintypes

    value = wintypes.DWORD(0)
    if not _user32().GetWindowDisplayAffinity(hwnd, value):
        return None
    return int(value.value)
