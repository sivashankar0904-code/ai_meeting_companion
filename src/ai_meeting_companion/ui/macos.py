from __future__ import annotations

import sys

NS_WINDOW_SHARING_NONE = 0


def set_capture_excluded(view_id: int, excluded: bool = True) -> bool:
    """Ask macOS not to share the window's contents (``NSWindow.sharingType``).

    ``view_id`` is Qt's ``winId()``, an NSView pointer. Returns True when the setting was applied.
    Note: since macOS 15 ScreenCaptureKit-based tools (newer Zoom/Teams/QuickTime) may still capture it.
    """
    if sys.platform != "darwin" or not view_id:
        return False
    try:
        import objc

        view = objc.objc_object(c_void_p=view_id)
        window = view.window()
        if window is None:
            return False
        window.setSharingType_(NS_WINDOW_SHARING_NONE if excluded else 1)
        # Show on every Space and above full-screen apps (meeting apps are often full screen).
        window.setCollectionBehavior_(1 << 0 | 1 << 8)  # canJoinAllSpaces | fullScreenAuxiliary
        window.setLevel_(25)  # NSStatusWindowLevel
        return True
    except Exception:
        return False
