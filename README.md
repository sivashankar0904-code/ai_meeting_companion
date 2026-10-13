# ai_meeting_companion

Windows meeting assistant: listens to audio, reads the screen, and suggests answers with three specialist Claude agents (Conversor, Screen Analyzer, Chat). Every session is logged to PostgreSQL.

## Setup
1. Create a venv and `pip install -e .[dev]`.
2. Install the Tesseract binary and make sure it is on PATH (or set `TESSERACT_CMD`).
3. Copy `.env.example` to `.env` and fill in `ANTHROPIC_API_KEY` and the DB settings. Postgres must be running.

4. Put your resume, job description and notes (`.md`/`.txt`) in `context/`. The Conversor and Chat agent use them to tailor suggested answers (see `context/README.md`).

## Run
```
python -m ai_meeting_companion run        # start a session with the overlay
python -m ai_meeting_companion run --no-overlay   # terminal only
python -m ai_meeting_companion sessions   # list past sessions
python -m ai_meeting_companion export <id>
```

Overlay hotkeys (change them in `.env`): `Ctrl+Shift+H` show/hide, `Ctrl+Shift+I` focus the input box, `Ctrl+Shift+T` click-through, `Ctrl+Shift+S` screenshot, `Ctrl+Shift+A` (or the **Suggest** button) send what was heard to the Conversor. Nothing is sent to the model until you press one of these. The overlay is excluded from screen capture and screen sharing on Windows 10 2004+; its header says "hidden from capture" when that worked.

## Build a Windows .exe
```
.\build_exe.ps1                # GPU libraries + Tesseract bundled when found (large folder, ~3 GB)
.\build_exe.ps1 -NoGpu         # much smaller; speech recognition runs on the CPU
.\build_exe.ps1 -Tesseract none
.\build_exe.ps1 -IncludeEnv    # also copies your .env (it holds your API key: don't share the folder)
```
Result: `dist\AIMeetingCompanion\AIMeetingCompanion.exe`. Your **`context\` folder is copied next to the exe** and read from there at every start, as are `.env` and the optional `tesseract\` folder, so you edit them without rebuilding. The exe has **no console window, no taskbar button and no tray icon**; the overlay is the only thing on screen. Quit with `Ctrl+Shift+Q` or the Quit button. If something is wrong it shows a message box, logs to `ai-meeting-companion.log`, and `AIMeetingCompanion.exe --selftest` writes a health report (`selftest.txt`). The first run downloads the speech model (about 460 MB).

Design and project context live in [docs/context/](docs/context/).
