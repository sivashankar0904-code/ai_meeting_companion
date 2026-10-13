from __future__ import annotations

import sys


def show_error(title: str, message: str) -> None:
    """Show a message box. The packaged exe has no console, so this is how startup problems reach the user."""
    if sys.platform != "win32":
        print(f"{title}: {message}", file=sys.stderr)
        return
    import ctypes

    MB_OK, MB_ICONERROR, MB_TOPMOST = 0x0, 0x10, 0x40000
    ctypes.windll.user32.MessageBoxW(None, message, title, MB_OK | MB_ICONERROR | MB_TOPMOST)
