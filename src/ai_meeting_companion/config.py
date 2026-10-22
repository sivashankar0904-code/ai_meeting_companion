from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values, find_dotenv
from sqlalchemy.engine import URL



def app_dir() -> Path:
    """Where the user's files live: .env, context/, tesseract/ and the log.

    Next to the .exe when frozen by PyInstaller, otherwise the project root
    (config.py -> ai_meeting_companion -> src -> project root)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = app_dir()


class ConfigError(RuntimeError):
    pass


def find_env_file() -> Path | None:
    """The .env next to the app (the exe, or the project root), else one in the current directory or a parent."""
    beside_app = PROJECT_ROOT / ".env"
    if beside_app.is_file():
        return beside_app
    found = find_dotenv(usecwd=True)
    return Path(found) if found else None


def resolve_tesseract(configured: str = "") -> str:
    """TESSERACT_CMD if set, else a ``tesseract/`` folder shipped next to the app, else "" (use PATH)."""
    if configured:
        return configured
    bundled = PROJECT_ROOT / "tesseract" / "tesseract.exe"
    return str(bundled) if bundled.is_file() else ""


@dataclass(frozen=True)
class DbSettings:
    host: str = "127.0.0.1"
    port: int = 5432
    user: str = "postgres"
    password: str = "postgres"
    name: str = "postgres"
    pool_min: int = 1
    pool_max: int = 10
    ssl_required: bool = False

    def url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.name,
            query={"sslmode": "require" if self.ssl_required else "prefer"},
        )


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    conversor_model: str = "claude-haiku-5-5"
    screen_model: str = "claude-sonnet-5-5"
    chat_model: str = "claude-sonnet-5-5"
    db: DbSettings = DbSettings()
    whisper_model: str = "small.en"
    whisper_device: str = "auto"  # auto | cuda | cpu
    whisper_hotwords: str = ""  # extra names/terms to spell correctly (space or comma separated)
    whisper_prompt: str = ""  # optional free text about the conversation
    session_memory_chars: int = 8000  # how much shared session history each LLM call includes
    whisper_auto_vocab: bool = True  # also learn terms from the context files
    hotkey: str = "<ctrl>+<shift>+s"
    suggest_hotkey: str = "<ctrl>+<shift>+a"
    tesseract_cmd: str = ""
    context_dir: str = "context"
    overlay_opacity: float = 0.94
    overlay_hide_from_capture: bool = True
    overlay_toggle_hotkey: str = "<ctrl>+<shift>+h"
    overlay_clickthrough_hotkey: str = "<ctrl>+<shift>+t"
    overlay_focus_hotkey: str = "<ctrl>+<shift>+i"
    overlay_quit_hotkey: str = "<ctrl>+<shift>+q"
    audio_mic: bool = True
    audio_mic_device: str = ""
    audio_chunk_secs: float = 6.0


def _flag(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer, got {raw!r}") from exc


def _text(env: Mapping[str, str], key: str, default: str) -> str:
    return env.get(key, "").strip() or default


def load_settings(env: Mapping[str, str] | None = None, *, require_api_key: bool = True) -> Settings:
    """Build Settings from the project's ``.env`` file.

    Keys are read from the file itself; system environment variables are ignored, so a
    stale ANTHROPIC_API_KEY set in Windows can never shadow the one in ``.env``.
    Passing a mapping instead of ``None`` skips the file (used by the tests).
    """
    if env is None:
        path = find_env_file()
        if path is None:
            raise ConfigError(f"No .env file found. Copy .env.example to {PROJECT_ROOT / '.env'} and fill it in.")
        env = {k: v or "" for k, v in dotenv_values(path).items()}

    api_key = env.get("ANTHROPIC_API_KEY", "").strip()
    if require_api_key and not api_key:
        raise ConfigError("ANTHROPIC_API_KEY is missing or empty in your .env file.")

    d = DbSettings()
    db = DbSettings(
        host=_text(env, "DB_HOST", d.host),
        port=_int(env, "DB_PORT", d.port),
        user=_text(env, "DB_USERNAME", d.user),
        password=env.get("DB_PASSWORD", d.password),
        name=_text(env, "DB_NAME", d.name),
        pool_min=_int(env, "DB_POOL_MIN_SIZE", d.pool_min),
        pool_max=_int(env, "DB_POOL_MAX_SIZE", d.pool_max),
        ssl_required=_flag(env.get("DB_SSL_REQUIRED"), d.ssl_required),
    )
    s = Settings(anthropic_api_key=api_key)
    return Settings(
        anthropic_api_key=api_key,
        conversor_model=_text(env, "CONVERSOR_MODEL", s.conversor_model),
        screen_model=_text(env, "SCREEN_MODEL", s.screen_model),
        chat_model=_text(env, "CHAT_MODEL", s.chat_model),
        db=db,
        whisper_model=_text(env, "WHISPER_MODEL", s.whisper_model),
        whisper_device=_text(env, "WHISPER_DEVICE", s.whisper_device).lower(),
        whisper_hotwords=env.get("WHISPER_HOTWORDS", "").strip(),
        whisper_prompt=env.get("WHISPER_PROMPT", "").strip(),
        session_memory_chars=max(_int(env, "SESSION_MEMORY_CHARS", s.session_memory_chars), 0),
        whisper_auto_vocab=_flag(env.get("WHISPER_AUTO_VOCAB"), s.whisper_auto_vocab),
        hotkey=_text(env, "SCREENSHOT_HOTKEY", s.hotkey),
        suggest_hotkey=_text(env, "SUGGEST_HOTKEY", s.suggest_hotkey),
        tesseract_cmd=resolve_tesseract(env.get("TESSERACT_CMD", "").strip()),
        context_dir=_text(env, "CONTEXT_DIR", s.context_dir),
        overlay_opacity=min(max(float(_text(env, "OVERLAY_OPACITY", str(s.overlay_opacity))), 0.2), 1.0),
        overlay_hide_from_capture=_flag(env.get("OVERLAY_HIDE_FROM_CAPTURE"), s.overlay_hide_from_capture),
        overlay_toggle_hotkey=_text(env, "OVERLAY_TOGGLE_HOTKEY", s.overlay_toggle_hotkey),
        overlay_clickthrough_hotkey=_text(env, "OVERLAY_CLICKTHROUGH_HOTKEY", s.overlay_clickthrough_hotkey),
        overlay_focus_hotkey=_text(env, "OVERLAY_FOCUS_HOTKEY", s.overlay_focus_hotkey),
        overlay_quit_hotkey=_text(env, "OVERLAY_QUIT_HOTKEY", s.overlay_quit_hotkey),
        audio_mic=_flag(env.get("AUDIO_MIC"), s.audio_mic),
        audio_mic_device=env.get("AUDIO_MIC_DEVICE", "").strip(),
        audio_chunk_secs=float(_text(env, "AUDIO_CHUNK_SECS", str(s.audio_chunk_secs))),
    )
