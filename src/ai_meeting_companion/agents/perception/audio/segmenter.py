from __future__ import annotations

from collections import deque

import numpy as np

RATE = 16_000
MAX_THRESHOLD = 0.05  # never require more than this, however noisy the room


class Segmenter:
    """Cuts a stream of short slices into utterances.

    An utterance is emitted as soon as speech is followed by a pause (``pause_secs``), so
    transcription starts right after the person stops talking instead of after a fixed
    window; ``max_secs`` bounds very long monologues. "Speech" is anything clearly above the
    room's noise floor, which is learned from the quietest recent slices, so it works on noisy
    laptop microphones as well as clean ones.
    """

    def __init__(
        self,
        *,
        max_secs: float = 12.0,
        pause_secs: float = 0.7,
        min_speech_secs: float = 0.3,
        min_level: float = 0.005,
        floor_factor: float = 1.8,
        floor_window: int = 40,
    ) -> None:
        self.max_samples = int(max_secs * RATE)
        self.pause_secs = pause_secs
        self.min_speech_secs = min_speech_secs
        self.min_level = min_level
        self.floor_factor = floor_factor
        self._levels: deque[float] = deque(maxlen=floor_window)
        self._reset()

    def _reset(self) -> None:
        self._parts: list[np.ndarray] = []
        self._samples = 0
        self._speech_secs = 0.0
        self._pause = 0.0
        self._speaking = False
        self._lead: np.ndarray | None = None  # last quiet slice, kept so words do not start abruptly

    def threshold(self) -> float:
        floor = float(np.percentile(self._levels, 20)) if len(self._levels) >= 8 else 0.0
        return min(max(self.min_level, floor * self.floor_factor), MAX_THRESHOLD)

    def feed(self, piece: np.ndarray) -> np.ndarray | None:
        """Add one slice; returns a finished utterance, or None."""
        level = float(np.sqrt(np.mean(np.square(piece)))) if piece.size else 0.0
        loud = level >= self.threshold()
        self._levels.append(level)
        secs = piece.size / RATE

        if loud:
            if not self._speaking:
                self._speaking = True
                if self._lead is not None:
                    self._parts.append(self._lead)
                    self._samples += self._lead.size
            self._pause = 0.0
            self._speech_secs += secs
            self._parts.append(piece)
            self._samples += piece.size
        elif self._speaking:
            self._pause += secs
            self._parts.append(piece)
            self._samples += piece.size
        else:
            self._lead = piece
            return None

        if self._pause >= self.pause_secs or self._samples >= self.max_samples:
            return self._emit()
        return None

    def flush(self) -> np.ndarray | None:
        """Emit whatever speech is buffered (call when the stream ends)."""
        return self._emit() if self._speaking else None

    def _emit(self) -> np.ndarray | None:
        enough = self._speech_secs >= self.min_speech_secs
        audio = np.concatenate(self._parts).astype(np.float32) if self._parts else None
        self._reset()
        return audio if enough else None
