# Conventions

- Python >= 3.11, src layout, type hints, small modules. The venv is managed by uv: install with `uv pip install --python .venv/Scripts/python.exe -e ".[dev]"`.
- Threads (no asyncio); the PyQt6 overlay receives events through Qt signals only.
- Overlay tests set `QT_QPA_PLATFORM=offscreen`; check real capture exclusion by hand (window flashes on screen).
- DB access only through `SessionStore`; SQLAlchemy models stay inside `models/` and `session/store.py`.
- Tests use fakes: `InMemorySessionStore`, `FakeListChatModel`, fake audio sources. `pytest` skips `db` tests; `pytest -m db` runs the Postgres store tests.
- Do not run `python -m ai_meeting_companion run` as a smoke test without intending to: it starts a real session (real API key, real DB row).

## Manual verification
1. Play an interview video; the Conversor prints roles and suggested answers.
2. Press the hotkey with a problem on screen; the Screen Analyzer solves it.
3. Type a question in the terminal; the Chat agent answers using recent transcript.
4. Stop, then `sessions` and `export <id>`; all events are present in Postgres.
