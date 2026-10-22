# Configuration

Read from the `.env` file by `config.py` (python-dotenv `dotenv_values`); system environment variables are ignored. The user creates `.env`; only `.env.example` is ever written or read by Claude.

- LLM: `ANTHROPIC_API_KEY` (required), `CONVERSOR_MODEL` (default `claude-haiku-5-5`), `SCREEN_MODEL` (default `claude-sonnet-5-5`), `CHAT_MODEL` (default `claude-sonnet-5-5`)
- Database: `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, `DB_NAME`, `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`, `DB_SSL_REQUIRED` (false for local Postgres; true maps to `sslmode=require`)
- App: `WHISPER_MODEL` (default `small.en`), `SESSION_MEMORY_CHARS` (shared history per request, default 8000), `WHISPER_DEVICE` (auto|cuda|cpu), `WHISPER_HOTWORDS`, `SCREENSHOT_HOTKEY`, `SUGGEST_HOTKEY` (default `<ctrl>+<shift>+a`), `TESSERACT_CMD`, `AUDIO_MIC` (default true), `AUDIO_MIC_DEVICE` (empty = Windows default, an index, or part of a name; list with `ai-meeting-companion devices`), `AUDIO_CHUNK_SECS`, `CONTEXT_DIR` (default `context`)

Postgres is already running in WSL docker. The Tesseract binary is a separate Windows install.

## Overlay settings
`OVERLAY_OPACITY` (0.2-1.0, default 0.94), `OVERLAY_HIDE_FROM_CAPTURE` (default true), `OVERLAY_TOGGLE_HOTKEY` (`<ctrl>+<shift>+h`), `OVERLAY_CLICKTHROUGH_HOTKEY` (`<ctrl>+<shift>+t`), `OVERLAY_FOCUS_HOTKEY` (`<ctrl>+<shift>+i`, brings the overlay forward and focuses the input box). Screenshot hotkey stays `SCREENSHOT_HOTKEY`.

## User context files (for the app, not Claude Code)
`./context/` (project root; override with `CONTEXT_DIR`) holds the user's own resume, job description and notes as `.md` files (other file types are ignored). `memory/documents.py` reads them at session start (name order, `README.md` and `_*` skipped, 30,000 chars total) and `with_background()` appends them to the Conversor and Chat system prompts. Screen Analyzer does not use them. Contents are git-ignored; restart the session after editing. The CLI prints which files were loaded, and the overlay shows it as the first feed entry (red warning when none), because the windowed exe has no console. The user's master resume lives in `Documents\projects\personal\resumes\resume.md`; `context/resume.md` is a copy (2026-10-13), so re-copy it after editing the original.
