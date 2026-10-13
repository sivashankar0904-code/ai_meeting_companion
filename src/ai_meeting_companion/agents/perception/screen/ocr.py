from __future__ import annotations

from typing import Callable

from PIL import Image

Ocr = Callable[[Image.Image], str]


def make_ocr(tesseract_cmd: str = "") -> Ocr:
    import pytesseract

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def ocr(image: Image.Image) -> str:
        try:
            return pytesseract.image_to_string(image)
        except pytesseract.TesseractNotFoundError as exc:
            raise RuntimeError(
                "Tesseract is not installed or not on PATH. Install it and/or set TESSERACT_CMD in .env."
            ) from exc

    return ocr
