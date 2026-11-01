"""Entry point for the packaged .exe (also works as ``python -m ai_meeting_companion.launcher``).

The exe is built windowed: no console, no taskbar button, no tray icon. Consequences handled here:
stdout/stderr do not exist (they go to a log file), a bare launch means "run", and startup problems
are shown in a message box instead of a console traceback.
"""

from __future__ import annotations

import logging
import multiprocessing
import sys
from pathlib import Path

from ai_meeting_companion.config import app_dir

LOG_NAME = "ai-meeting-companion.log"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


HOW_TO_MAC = """AI Meeting Companion (macOS)

This folder holds everything you edit, next to AIMeetingCompanion.app; the app itself never changes it.
Keep the .app and these files together when you move the folder.
1. If there is no .env here, copy .env.example to .env and fill in ANTHROPIC_API_KEY and the DB_* settings.
2. Put your resume / job description / notes (.md files) in the context folder, then restart the app.
3. Open AIMeetingCompanion.app. It has no Dock icon: the overlay appears top-right. Quit: Ctrl+Shift+Q.
4. Grant Microphone (asked on first use), Screen Recording and Accessibility (System Settings > Privacy & Security;
   add the app to both Accessibility and Input Monitoring so the hotkeys work).
5. Meeting audio needs BlackHole 2ch and a Multi-Output Device (see the project README).
6. Problems? See ai-meeting-companion.log in this folder.
"""


def seed_user_folder() -> None:
    """macOS app: create the user-editable folder on first launch (the bundle cannot hold .env or context/)."""
    folder = app_dir()
    (folder / "context").mkdir(exist_ok=True)
    bundled = Path(getattr(sys, "_MEIPASS", "")) / ".env.example"
    if bundled.is_file() and not (folder / ".env.example").exists():
        (folder / ".env.example").write_bytes(bundled.read_bytes())
    if not (folder / "HOW_TO_RUN.txt").exists():
        (folder / "HOW_TO_RUN.txt").write_text(HOW_TO_MAC, encoding="utf-8")


def prepare_windowed_process(log_path: Path) -> None:
    """Give a console-less process usable stdout/stderr and route logging to a file.

    PyInstaller windowed apps start with ``sys.stdout`` and ``sys.stderr`` set to None, which makes
    print() calls and progress bars (model downloads) raise."""
    if sys.stdout is None or sys.stderr is None:
        stream = open(log_path, "a", encoding="utf-8", buffering=1)  # noqa: SIM115 - lives for the process
        if sys.stdout is None:
            sys.stdout = stream
        if sys.stderr is None:
            sys.stderr = stream
    logging.basicConfig(
        level=logging.WARNING,
        handlers=[logging.FileHandler(log_path, encoding="utf-8")],
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )


def main(argv: list[str] | None = None) -> int:
    multiprocessing.freeze_support()
    args = list(sys.argv[1:] if argv is None else argv)
    log_path = app_dir() / LOG_NAME
    if is_frozen():
        prepare_windowed_process(log_path)
        if sys.platform == "darwin":
            seed_user_folder()

    if "--selftest" in args:
        from ai_meeting_companion.selftest import run_selftest

        return run_selftest(show_dialog="--quiet" not in args)

    from ai_meeting_companion.cli import main as cli_main

    try:
        return cli_main(args or ["run"])
    except SystemExit:
        raise
    except Exception as exc:
        logging.getLogger(__name__).exception("fatal error")
        if is_frozen():
            from ai_meeting_companion.ui.fatal import show_error

            show_error("AI Meeting Companion", f"{type(exc).__name__}: {exc}\n\nDetails: {log_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
