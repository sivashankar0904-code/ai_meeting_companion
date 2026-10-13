from __future__ import annotations

import queue
import threading
from typing import Callable, Iterator, Protocol

import numpy as np

from ai_meeting_companion.agents.perception.audio.segmenter import Segmenter

TARGET_RATE = 16_000
SLICE_SECS = 0.25  # read granularity so stop requests are noticed quickly
SILENCE_RMS = 0.005
NO_SOUND_WARN_SECS = 30.0  # tell the user when a device has been silent this long
FLUSH_IDLE_SECS = 0.75  # sound stopped this long ago: send what we have
MIN_FLUSH_SECS = 0.5  # ...but only if it is at least this much audio


class AudioSource(Protocol):
    channel: str

    def chunks(self, stop: threading.Event) -> Iterator[np.ndarray]:
        """Yield mono float32 chunks at 16 kHz until ``stop`` is set."""
        ...


def resample(samples: np.ndarray, src_rate: int, dst_rate: int = TARGET_RATE) -> np.ndarray:
    if src_rate == dst_rate or samples.size == 0:
        return samples.astype(np.float32, copy=False)
    n_out = int(samples.size * dst_rate / src_rate)
    x_old = np.linspace(0.0, 1.0, samples.size, endpoint=False)
    x_new = np.linspace(0.0, 1.0, n_out, endpoint=False)
    return np.interp(x_new, x_old, samples).astype(np.float32)


def is_silent(samples: np.ndarray) -> bool:
    return samples.size == 0 or float(np.sqrt(np.mean(np.square(samples)))) < SILENCE_RMS


class LoopbackSource:
    """System audio (what the meeting participants say) via WASAPI loopback.

    Loopback delivers no data at all while nothing is playing, so a blocking read would hang
    forever in silence. Audio is collected through a callback instead, and a partial chunk is
    flushed once the sound stops so the end of a sentence is not held back.
    """

    channel = "loopback"

    def __init__(self, chunk_secs: float = 6.0) -> None:
        self.chunk_secs = chunk_secs
        self.on_status: Callable[[str], None] | None = None  # set by the AudioAgent

    def _say(self, message: str) -> None:
        if self.on_status is not None:
            self.on_status(message)

    def chunks(self, stop: threading.Event) -> Iterator[np.ndarray]:
        import pyaudiowpatch as pyaudio

        pa = pyaudio.PyAudio()
        stream = None
        incoming: queue.Queue[bytes] = queue.Queue()

        def on_audio(in_data, frame_count, time_info, status):
            incoming.put(in_data)
            return (None, pyaudio.paContinue)

        try:
            wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            device = pa.get_device_info_by_index(wasapi["defaultOutputDevice"])
            if not device.get("isLoopbackDevice"):
                for candidate in pa.get_loopback_device_info_generator():
                    if device["name"] in candidate["name"]:
                        device = candidate
                        break
                else:
                    raise RuntimeError("No WASAPI loopback device found for the default output device.")
            rate = int(device["defaultSampleRate"])
            channels = int(device["maxInputChannels"])
            name = str(device["name"])
            self._say(f"Listening on: {name}")
            stream = pa.open(
                format=pyaudio.paInt16, channels=channels, rate=rate, input=True,
                input_device_index=device["index"], frames_per_buffer=1024, stream_callback=on_audio,
            )
            target = int(rate * self.chunk_secs)
            parts: list[np.ndarray] = []
            have = 0
            idle = 0.0
            quiet_for = 0.0  # seconds since any data arrived (loopback sends nothing when silent)
            warned_at = 0.0
            while not stop.is_set():
                try:
                    raw = incoming.get(timeout=SLICE_SECS)
                except queue.Empty:
                    idle += SLICE_SECS
                    quiet_for += SLICE_SECS
                    if quiet_for >= NO_SOUND_WARN_SECS and (warned_at == 0.0 or quiet_for - warned_at >= 30.0):
                        warned_at = quiet_for
                        self._say(
                            f"No sound from {name} for {int(quiet_for)}s. Is the meeting audio playing "
                            "on this output device?"
                        )
                    if parts and idle >= FLUSH_IDLE_SECS and have >= MIN_FLUSH_SECS * rate:
                        yield resample(np.concatenate(parts), rate)
                        parts, have = [], 0
                    continue
                idle = 0.0
                quiet_for = 0.0
                warned_at = 0.0
                pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                mono = pcm.reshape(-1, channels).mean(axis=1)
                parts.append(mono)
                have += mono.size
                if have >= target:
                    yield resample(np.concatenate(parts), rate)
                    parts, have = [], 0
        finally:
            if stream is not None:
                stream.stop_stream()
                stream.close()
            pa.terminate()


def list_input_devices() -> list[tuple[int, str, str]]:
    """(index, name, host API) for every device that can record."""
    import sounddevice as sd

    apis = sd.query_hostapis()
    return [
        (i, d["name"], apis[d["hostapi"]]["name"])
        for i, d in enumerate(sd.query_devices())
        if d["max_input_channels"] > 0
    ]


def resolve_input_device(spec: str) -> int | None:
    """``""`` -> system default; digits -> device index; otherwise the first input device
    whose name contains ``spec`` (case-insensitive)."""
    spec = spec.strip()
    if not spec:
        return None
    if spec.isdigit():
        return int(spec)
    for index, name, _api in list_input_devices():
        if spec.lower() in name.lower():
            return index
    raise RuntimeError(f"No input device matches AUDIO_MIC_DEVICE={spec!r}. Run: ai-meeting-companion devices")


class MicSource:
    """The user's own microphone."""

    channel = "mic"

    def __init__(self, chunk_secs: float = 6.0, device: str = "") -> None:
        self.chunk_secs = chunk_secs
        self.device = device
        self.on_status: Callable[[str], None] | None = None

    def chunks(self, stop: threading.Event) -> Iterator[np.ndarray]:
        import sounddevice as sd

        index = resolve_input_device(self.device)
        info = sd.query_devices(index if index is not None else sd.default.device[0], "input")
        if self.on_status is not None:
            self.on_status(f"Microphone: {info['name']}")
        slice_frames = int(TARGET_RATE * SLICE_SECS)
        # Send each utterance when the speaker pauses; chunk_secs only bounds very long monologues.
        segmenter = Segmenter(max_secs=max(2 * self.chunk_secs, 12.0))
        with sd.InputStream(samplerate=TARGET_RATE, channels=1, dtype="float32", device=index) as stream:
            while not stop.is_set():
                data, _ = stream.read(slice_frames)
                utterance = segmenter.feed(data[:, 0].copy())
                if utterance is not None:
                    yield utterance
