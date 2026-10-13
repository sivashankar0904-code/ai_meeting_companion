"""PyInstaller entry point (kept outside the package so the whole package is analysed as a dependency)."""

from ai_meeting_companion.launcher import main

if __name__ == "__main__":
    raise SystemExit(main())
