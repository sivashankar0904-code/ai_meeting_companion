"""``--selftest``: checks that a build (or a fresh install) has everything it needs, without calling the LLM.

Writes selftest.txt next to the app and prints the same report. Never prints secret values."""

from __future__ import annotations

import importlib
import subprocess
import sys
from typing import Callable

from ai_meeting_companion.config import PROJECT_ROOT, find_env_file, load_settings, resolve_tesseract

Check = Callable[[], str]

MODULES = [
    "PyQt6.QtWidgets", "faster_whisper", "ctranslate2", "sounddevice", "pyaudiowpatch", "mss", "pytesseract",
    "pynput.keyboard", "sqlalchemy.dialects.postgresql", "psycopg", "langchain_anthropic", "anthropic", "dotenv",
]
PROMPTS = ["conversor", "screen_analyzer", "chat", "shared_memory"]


def _imports() -> str:
    for name in MODULES:
        importlib.import_module(name)
    return f"{len(MODULES)} libraries import"


def _prompts() -> str:
    from ai_meeting_companion.prompts.loader import build_system_prompt

    for name in PROMPTS[:3]:
        build_system_prompt(name)
    return "prompt files found"


def _env() -> str:
    path = find_env_file()
    if path is None:
        raise RuntimeError(f"no .env next to the app; copy .env.example to {PROJECT_ROOT / '.env'} and fill it in")
    load_settings()  # raises a clear message if the API key is missing
    return f"{path.name} found and valid"


def _context() -> str:
    from ai_meeting_companion.memory.documents import load_context_docs

    settings = load_settings(require_api_key=False) if find_env_file() else None
    folder = PROJECT_ROOT / (settings.context_dir if settings else "context")
    docs = load_context_docs(folder)
    if not folder.is_dir():
        raise RuntimeError(f"context folder not found: {folder}")
    return f"{folder} ({', '.join(docs.files) if docs else 'no files yet'})"


def _tesseract() -> str:
    settings = load_settings(require_api_key=False) if find_env_file() else None
    command = resolve_tesseract(settings.tesseract_cmd if settings else "") or "tesseract"
    version = subprocess.run([command, "--version"], capture_output=True, text=True, timeout=20, check=True)
    return f"{command}: {version.stdout.splitlines()[0]}"


def _gpu() -> str:
    from ai_meeting_companion.agents.perception.audio.transcriber import add_cuda_dll_dirs, cuda_available

    add_cuda_dll_dirs()
    if not cuda_available():
        return "no CUDA device: speech recognition will use the CPU (slower)"
    import ctypes

    ctypes.WinDLL("cublas64_12.dll")
    return "CUDA device and cuBLAS available: speech recognition will use the GPU"


def _audio() -> str:
    import pyaudiowpatch as pyaudio
    import sounddevice as sd

    pa = pyaudio.PyAudio()
    try:
        loopbacks = [d["name"] for d in pa.get_loopback_device_info_generator()]
    finally:
        pa.terminate()
    mics = [d for d in sd.query_devices() if d["max_input_channels"] > 0]
    return f"{len(loopbacks)} loopback device(s), {len(mics)} input device(s)"


def _database() -> str:
    from sqlalchemy import create_engine, text

    if find_env_file() is None:
        raise RuntimeError("skipped: no .env")
    engine = create_engine(load_settings(require_api_key=False).db.url())
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    finally:
        engine.dispose()
    return "PostgreSQL reachable"


CHECKS: list[tuple[str, Check]] = [
    ("libraries", _imports),
    ("prompts", _prompts),
    (".env", _env),
    ("context folder", _context),
    ("tesseract", _tesseract),
    ("gpu", _gpu),
    ("audio devices", _audio),
    ("database", _database),
]


def run_selftest(show_dialog: bool = True) -> int:
    lines = [f"AI Meeting Companion self-test ({'exe' if getattr(sys, 'frozen', False) else 'source'})",
             f"app folder: {PROJECT_ROOT}", ""]
    failed = 0
    for name, check in CHECKS:
        try:
            lines.append(f"OK    {name}: {check()}")
        except Exception as exc:
            failed += 1
            lines.append(f"FAIL  {name}: {type(exc).__name__}: {exc}")
    lines += ["", "all checks passed" if not failed else f"{failed} check(s) failed"]
    report = "\n".join(lines)
    (PROJECT_ROOT / "selftest.txt").write_text(report, encoding="utf-8")
    print(report)
    if show_dialog and getattr(sys, "frozen", False):  # the exe has no console to read the report from
        from ai_meeting_companion.ui.fatal import show_error

        show_error("AI Meeting Companion self-test", report)
    return 1 if failed else 0
