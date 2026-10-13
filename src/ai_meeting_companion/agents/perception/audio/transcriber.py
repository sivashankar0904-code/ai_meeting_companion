from __future__ import annotations

import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Protocol, Sequence

import numpy as np

log = logging.getLogger(__name__)

RATE_SECOND = 16_000  # one second of audio at the recogniser's sample rate
SMALL_MODELS = {"tiny", "tiny.en", "base", "base.en"}  # hotwords make these loop

TARGET_RMS = 0.08  # quiet microphones are boosted towards this level before recognition
MAX_GAIN = 8.0  # never amplify further, so pure noise is not turned into "speech"


def add_cuda_dll_dirs() -> None:
    """Make pip-installed NVIDIA libraries (nvidia-cublas-cu12, nvidia-cudnn-cu12) findable.

    They unpack to site-packages/nvidia/<name>/bin, which Windows does not search by itself.
    """
    if sys.platform != "win32":
        return
    roots: list[str] = []
    if getattr(sys, "frozen", False):  # the packaged exe carries them under <bundle>/nvidia/<name>/bin
        roots.append(str(Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "nvidia"))
    spec = importlib.util.find_spec("nvidia")
    roots += list(spec.submodule_search_locations or []) if spec else []
    for root in roots:
        for bin_dir in Path(root).glob("*/bin"):
            os.add_dll_directory(str(bin_dir))
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")


def cuda_available() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


class Transcriber(Protocol):
    def transcribe(self, samples: np.ndarray) -> str: ...

    # Optional: ``load()`` to fetch/initialise the model before the first chunk arrives.


def boost_quiet(samples: np.ndarray) -> np.ndarray:
    """Raise the level of quiet audio (capped), leaving normal-level audio untouched."""
    rms = float(np.sqrt(np.mean(np.square(samples)))) if samples.size else 0.0
    if rms <= 1e-6 or rms >= TARGET_RMS:
        return samples
    return np.clip(samples * min(TARGET_RMS / rms, MAX_GAIN), -1.0, 1.0).astype(np.float32)


def collapse_repeats(parts: list[str], limit: int = 2) -> list[str]:
    """Whisper sometimes loops on one phrase; keep at most ``limit`` identical neighbours."""
    out: list[str] = []
    run = 0
    for text in parts:
        run = run + 1 if out and out[-1] == text else 1
        if run <= limit:
            out.append(text)
    return out


def is_hallucination(no_speech_prob: float, avg_logprob: float) -> bool:
    """Whisper invents phrases ("thank you", "love you") on noise; these segments score badly."""
    return avg_logprob < -1.3 or (no_speech_prob > 0.5 and avg_logprob < -0.8)


class WhisperTranscriber:
    """faster-whisper on CPU (int8). The model loads on first use.

    ``terms`` are names and jargon Whisper should spell correctly (taken from the user's own
    context files and settings); ``prompt`` is optional free text describing the conversation.
    Nothing about the subject matter is built in.
    """

    def __init__(
        self, model_size: str = "small.en", terms: Sequence[str] = (), prompt: str = "", device: str = "auto"
    ) -> None:
        self.model_size = model_size
        self.requested_device = device
        self.device = "not loaded"
        self.terms = [t for t in terms if t]
        self.prompt = prompt.strip()
        self._model = None

    @property
    def initial_prompt(self) -> str | None:
        parts = [self.prompt, ", ".join(self.terms)]
        return " ".join(p for p in parts if p) or None

    @property
    def hotwords(self) -> str | None:
        if not self.terms or self.model_size in SMALL_MODELS:
            return None
        return " ".join(self.terms)

    def _candidate_devices(self) -> list[str]:
        if self.requested_device == "cpu":
            return ["cpu"]
        if self.requested_device == "cuda":
            return ["cuda", "cpu"]
        return ["cuda", "cpu"] if cuda_available() else ["cpu"]  # auto

    def load(self) -> None:
        """Load the model on the GPU if possible, otherwise the CPU."""
        if self._model is not None:
            return
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        from faster_whisper import WhisperModel

        add_cuda_dll_dirs()
        for device in self._candidate_devices():
            try:
                model = WhisperModel(self.model_size, device=device, compute_type="float16" if device == "cuda" else "int8")
                # CUDA libraries load lazily; run a tiny transcription now so a missing DLL fails here, not mid-meeting.
                list(model.transcribe(np.zeros(RATE_SECOND, dtype=np.float32), language="en")[0])
            except Exception as exc:
                log.warning("Whisper on %s failed (%s: %s)", device, type(exc).__name__, exc)
                continue
            self._model, self.device = model, device
            return
        raise RuntimeError("Could not load the speech model on the GPU or the CPU.")

    def transcribe(self, samples: np.ndarray) -> str:
        self.load()
        segments, _ = self._model.transcribe(
            boost_quiet(samples),
            language="en",
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=self.initial_prompt,
            hotwords=self.hotwords,
        )
        kept = []
        for s in segments:
            if is_hallucination(s.no_speech_prob, s.avg_logprob):
                log.info("dropped low-confidence segment %r (no_speech=%.2f logprob=%.2f)",
                         s.text.strip(), s.no_speech_prob, s.avg_logprob)
                continue
            kept.append(s.text.strip())
        return " ".join(collapse_repeats(kept)).strip()
