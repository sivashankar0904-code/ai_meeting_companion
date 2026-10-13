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
