from __future__ import annotations

from PIL import Image


def grab_screen() -> Image.Image:
    """Capture the primary monitor."""
    import mss

    grabber = getattr(mss, "MSS", None) or mss.mss  # mss.mss is deprecated in newer releases
    with grabber() as sct:
        shot = sct.grab(sct.monitors[1])
    return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
