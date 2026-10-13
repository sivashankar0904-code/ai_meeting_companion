from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Sequence

import numpy as np

from ai_meeting_companion.agents.perception.audio.capture import AudioSource, is_silent
from ai_meeting_companion.agents.perception.audio.transcriber import Transcriber
from ai_meeting_companion.core.agent import POLL_SECS, BaseAgent
from ai_meeting_companion.core.bus import Bus
from ai_meeting_companion.core.events import STATUS, TRANSCRIPT, Event

log = logging.getLogger(__name__)


class AudioAgent(BaseAgent):
    """One reader thread per source feeds chunks to a single transcriber loop,
    which publishes a transcript event (tagged with the source channel) per non-empty chunk."""

    name = "audio"

    def __init__(
        self, bus: Bus, sources: Sequence[AudioSource], transcriber: Transcriber, *, silence_note_secs: float = 30.0
    ) -> None:
        super().__init__(bus)
        self._silence_note_secs = silence_note_secs
        self._silent_since: dict[str, float] = {}
        self._sources = sources
        self._transcriber = transcriber
        self._chunks: queue.Queue[tuple[str, np.ndarray]] = queue.Queue(maxsize=8)
        self._readers: list[threading.Thread] = []
        self._last_silent_note = 0.0

    def _status(self, text: str) -> None:
        self.publish(Event(kind=STATUS, source=self.name, payload={"text": text}))

    def run(self) -> None:
        load = getattr(self._transcriber, "load", None)
        if load is not None:
            self._status("Loading speech model (the first run downloads about 150 MB)...")
            try:
                load()
                device = getattr(self._transcriber, "device", None)
                if device:
                    self._status(f"Speech model ready ({'GPU' if device == 'cuda' else 'CPU'})")
            except Exception as exc:
                log.exception("could not load the speech model")
                self.report_error(f"speech model: {type(exc).__name__}: {exc}")
                return
        self._status("Listening to meeting audio...")
        for source in self._sources:
            if hasattr(source, "on_status"):
                source.on_status = self._status
            t = threading.Thread(target=self._read, args=(source,), name=f"audio-{source.channel}", daemon=True)
            t.start()
            self._readers.append(t)
        while not self.stopping:
            try:
                channel, samples = self._chunks.get(timeout=POLL_SECS)
            except queue.Empty:
                continue
            self._guarded(self._transcribe, channel, samples)

    def _transcribe(self, channel: str, samples: np.ndarray) -> None:
        text = self._transcriber.transcribe(samples).strip()
        if text:
            self.publish(Event(kind=TRANSCRIPT, source=self.name, payload={"text": text, "channel": channel}))
        else:
            self._status(f"Heard sound on {channel} but no speech was recognised (music or noise?)")

    def _read(self, source: AudioSource) -> None:
        try:
            for samples in source.chunks(self._stop):
                if is_silent(samples):
                    # Routine: nobody is talking. Only mention it after a long quiet stretch.
                    now = time.monotonic()
                    since = self._silent_since.setdefault(source.channel, now)
                    if now - since >= self._silence_note_secs and now - self._last_silent_note >= self._silence_note_secs:
                        self._last_silent_note = now
                        self._status(
                            f"No {source.channel} sound for {int(now - since)}s. If someone is talking, "
                            "check the call isn't muted or playing on another device."
                        )
                    continue
                self._silent_since.pop(source.channel, None)
                level = float(np.sqrt(np.mean(np.square(samples))))
                self._status(f"Hearing {source.channel} audio (level {level:.3f}), transcribing...")
                try:
                    self._chunks.put_nowait((source.channel, samples))
                except queue.Full:
                    log.warning("transcriber is behind; dropping a %s chunk", source.channel)
        except Exception as exc:
            log.exception("audio source %s failed", source.channel)
            self.report_error(f"audio source {source.channel}: {type(exc).__name__}: {exc}")
