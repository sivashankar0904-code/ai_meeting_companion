# Architecture

## Principles
- Perception vs reasoning split: sensor agents (audio, screen, manual input) only publish events; specialist agents only consume events and publish `llm_response`. Agents never call each other; they talk through the event bus.
- One folder per agent, so a new agent is one new folder.
- Prompts are files (`prompts/*.md`).
- Everything is an event, so the session logger is one subscriber and gets a complete record.
- Capture, OCR, transcription, LLM and the session store sit behind small interfaces so tests use fakes.

## Layout (`src/ai_meeting_companion/`)
- `cli.py`, `__main__.py`: `run [--title --no-audio --no-screen --no-overlay] | sessions | export <id> [-o file]`. `run` also reads typed stdin lines as `user_message`.
- `config.py`: `load_settings()` reads keys from the `.env` file only (not the system environment) and returns typed `Settings`/`DbSettings` (`DbSettings.url()` builds the SQLAlchemy URL).
- `core/`: `events.py` (Event; kinds `transcript|screen_text|user_message|llm_response|error`), `bus.py` (thread-safe pub/sub), `agent.py` (BaseAgent: worker thread, `handle`/`idle`, errors become `error` events), `orchestrator.py` (one session: create thread, start logger first, start agents, stop, drain logger, end thread).
- `agents/factory.py`: builds the real agent set from Settings.
- `agents/perception/`: `audio/` (capture: WASAPI loopback + optional mic; transcriber: faster-whisper; agent), `screen/` (hotkey, capture, ocr, agent), `manual_input.py`.
- `agents/specialists/`: `base.py` (SpecialistAgent: trigger kind, `ask`, `finalize` hook, prepends the shared timeline), `conversor.py` (buffers transcript, sends only on request, roles state), `screen_analyzer.py`, `chat.py`.
- `llm/`: `models.py` (ChatAnthropic factory), `chains.py` (prompt | model).
- `prompts/`: `loader.py` plus `conversor.md`, `screen_analyzer.md`, `chat.md`.
- `memory/session_memory.py`: **shared session memory** (see below). `memory/documents.py`: loads the user's context files (resume, job description) from `./context/`.
- `models/`, `records/`: ORM models and dataclasses (see database.md).
- `session/`: `store.py`, `logger.py` (subscribes to all events), `export.py`.
- `ui/`: the PyQt6 overlay. `overlay.py` (OverlayWindow: frameless, always on top, translucent, dark; OverlayController holds thread-safe signals), `app.py` (`run_overlay`: builds the window, adds a `BusForwarder`, starts global hotkeys, runs the Qt loop, then stops the orchestrator), `forwarder.py` (bus -> Qt signal), `hotkeys.py` (pynput global hotkeys), `win32.py` (`SetWindowDisplayAffinity`), `console.py` (terminal output, used with `--no-overlay`).

## Adding an agent
Add a prompt file, a model setting, and a `SpecialistAgent` subclass or instance registered in `agents/factory.py` with its input event kind.

## Screen Analyzer answer format
`prompts/screen_analyzer.md` forces, for coding problems: **Problem** (1 line) -> **Pseudocode** (<=6 lines) -> **Code** -> **Explanation** (exactly 4 one-line bullets: idea, why correct, edge cases, complexity incl. brute-force cost) -> **Alternate method** (1 line with trade-off); under ~120 words of prose so an interviewer has no follow-up to ask. Other problem types (SQL, MCQ, system design, errors) map onto the same section names. Measured: coding answer ~800 output tokens, ~6 s. Any prompt can be overridden without rebuilding by placing `prompts/<name>.md` beside the app/exe (`load_prompt`).

## Packaging as an exe (`build_exe.ps1` -> `scripts/build_exe.py`, PyInstaller onedir, windowed)
- Output `dist/AIMeetingCompanion/`: the exe plus everything the user edits **beside** it: `.env`, `context/` (copied from the repo at build time), optional `tesseract/`, `HOW_TO_RUN.txt`. Nothing user-editable is baked in.
- `config.app_dir()`/`PROJECT_ROOT` = folder of the exe when frozen (`sys.frozen`), else the repo root; `.env` is looked up there first, `context/` and `tesseract/` are resolved from it (`resolve_tesseract`).
- Windowed = no console; `launcher.py` sends stdout/stderr to `ai-meeting-companion.log` (a windowed process has `sys.stdout is None`, which crashes prints and download progress bars), defaults a bare launch to `run`, and shows startup errors in a message box (`ui/fatal.py`). `--selftest` (selftest.py) checks libraries, prompts, .env, context folder, Tesseract, GPU, audio devices and the database without calling the LLM.
- No tray icon is ever created (a test forbids `QSystemTrayIcon`), the overlay is a `Qt.Tool` window (no taskbar button, not in Alt+Tab), and `setQuitOnLastWindowClosed(False)` keeps the app alive while the overlay is hidden. Quit: `OVERLAY_QUIT_HOTKEY` (`Ctrl+Shift+Q`), the Quit button, or closing the window (`closeEvent` emits `quit_requested`, so Alt+F4 / taskkill / Windows shutdown end the app and save the session; the hide hotkey does not quit).
- Verified on the built exe (Windows 11): overlay is `WS_EX_TOOLWINDOW` without `WS_EX_APPWINDOW`, topmost, capture-excluded (0x11), zero tray windows, no console child process; `WM_CLOSE` exits with code 0 and the session is marked ended. Build is ~2.4 GB with GPU libs + Tesseract (`--no-gpu` is much smaller).
- GPU libraries (cuBLAS/cuDNN, ~1.5 GB) are bundled under `nvidia/<pkg>/bin`; `add_cuda_dll_dirs()` finds them in `sys._MEIPASS`. `--no-gpu` skips them (CPU fallback is automatic).
- Whisper models are not bundled: first run downloads them into the Hugging Face cache.

## Shared session memory
- All agents share ONE timeline (`SessionMemory`), instead of private histories: what was heard (per channel), text read from the screen, what the user typed, and every assistant's replies, with timestamps. It is filled by `bus.add_tap(memory.record)` (synchronous at publish time, so it is always current before an agent reacts). Created by the `Orchestrator`, passed to `build_agents(settings, bus, memory, ...)`.
- Each LLM request = system prompt (+ `prompts/shared_memory.md` + background docs) + `Session so far:` timeline + the new request. The request's own entries are excluded from the timeline so nothing is duplicated.
- Budget `SESSION_MEMORY_CHARS` (default 8000 chars, ~2000 tokens; 0 disables). The newest screen capture gets up to 3000 chars, older ones 400; each agent's newest reply 1500, older 300; speech lines 500. Newest entries win when the budget is short.
- Why: before this the Conversor never knew a screenshot had been taken, so "explain this problem" got the previous topic. Verified with the real model (scenario in `tests/unit/test_session_memory.py`).

## Overlay
- `run` opens the overlay by default; `--no-overlay` gives the terminal UI (console printer + typed input). In overlay mode the terminal only prints hotkeys and the saved session id.
- Capture exclusion: `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` is applied on every `showEvent` (window flag changes recreate the native window). Verified on Windows 11: the overlay is absent from `mss` captures (so the screenshot/OCR feature never reads the overlay) and the header shows "hidden from capture" (green) or "VISIBLE to screen share" (red) if Windows refused. Needs Windows 10 2004+.
- Dragging: press and drag anywhere on the panel that is not a button, the feed or the input box (manual move in `OverlayWindow.mouse*Event`, not `startSystemMove`). The position is saved to `overlay_position.json` beside the app/exe on release and restored on start if still on a connected screen; delete that file to reset to the top-right corner.
- Threading: agents run on worker threads and reach the GUI only through `OverlayController` signals; pynput hotkey callbacks only emit signals.
- Ctrl+C in the terminal, the Quit button, or closing quits cleanly and saves the session.

## Audio notes
- WASAPI loopback delivers **no data while nothing plays**, so `LoopbackSource` uses a callback + queue (never a blocking read) and flushes a partial chunk 0.75 s after sound stops.
- `AudioAgent` loads the Whisper model first and publishes `status` events ("Loading speech model...", "Listening..."); status events show in the overlay/console and are never logged. First run downloads ~140 MB into the Hugging Face cache (already done on this machine).
- Verified end to end on this machine: a spoken sentence played through the speakers was captured via loopback and transcribed exactly. The mic path is verified too (a sentence played through the speakers was heard by the Realtek mic and transcribed). Loopback = other people (`[loopback]`), mic = the user's own voice (`[mic]`); the user's voice is NOT in loopback. With speakers (no headphones) the mic also hears the meeting, so it is transcribed twice.
- Audio follows the *default output device*; if meeting audio plays on a different device (e.g. a headset chosen inside Teams), loopback will not hear it.

## Transcription quality (learned from testing on this machine)
- Whisper hallucinates phrases ("love you", "thank you", "go on") on quiet/noisy audio. `WhisperTranscriber` drops low-confidence segments (`is_hallucination`), boosts quiet input up to 8x (`boost_quiet`), uses `vad_filter`, `condition_on_previous_text=False` and `beam_size=5`, and collapses repeated phrases.
- `base.en` misheard "FastAPI" as "first API". `small.en` + `hotwords` (`DEFAULT_HOTWORDS`, override with `WHISPER_HOTWORDS`) got it right. Hotwords on `base`/`tiny` models make Whisper loop, so they default to off there.
- Default model is `small.en` (~460 MB, ~3 s per 15 s of audio on CPU). A `WHISPER_MODEL=base.en` line in `.env` overrides it.

## Conversor behaviour
- **Manual only, to save tokens.** Transcript chunks are buffered locally (and still logged); the model is called only when a `suggest_request` event arrives: overlay **Suggest** button, `SUGGEST_HOTKEY` (`Ctrl+Shift+A`), or `/suggest` typed in terminal mode. It sends only what was heard since the last request (buffer capped at ~8000 chars, history capped at 3000 tokens); a request with nothing new sends nothing and says so; a failed request keeps the transcript for the retry. Screen Analyzer (screenshot hotkey) and Chat (typed) were already manual, so no agent calls the LLM on its own.
- Earlier versions answered only the interviewer's (`loopback`) questions and returned `NO_QUESTION` for anything on `mic`; with manual sending that just looked broken when testing alone, so it was removed.
- Because sending is manual, the prompt answers the most recent question from ANY channel (a mic question when testing alone is answered too). `NO_QUESTION` is only for an empty/unintelligible transcript, and shows as a status line.

## Transcription speed (measured on this machine: RTX 3050 6GB laptop, 12 CPU threads)
- Whisper runs on the **GPU** when available (`WHISPER_DEVICE=auto`, float16) and falls back to CPU (int8) if CUDA libraries are missing. It needs pip packages `nvidia-cublas-cu12` and `nvidia-cudnn-cu12` (extra `.[gpu]`); `add_cuda_dll_dirs()` puts their DLL folders on the search path. Load does a 1 s test transcription so a missing DLL fails at startup, not mid-meeting. Status line shows "Speech model ready (GPU|CPU)".
- Per 6 s of audio: `small.en` GPU 0.25 s vs CPU 2.5 s; `medium.en` GPU 0.7 s vs CPU 10 s (medium spelt "FastAPI" closer to right, ~1.5 GB download).
- Mic audio is cut into utterances by `segmenter.py` (emit after a 0.7 s pause, adaptive noise floor, max 12 s) instead of fixed 6 s windows. Loopback still uses 6 s chunks with a 0.75 s idle flush. End-to-end: transcript appears ~0.7-1.1 s after speech ends.

## Known limits
- Audio is transcribed in fixed ~6 s chunks, so a word can be split across chunks.
- System audio has no speaker diarization; roles come from the channel tag and content.
