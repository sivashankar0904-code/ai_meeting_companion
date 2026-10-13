from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from uuid import UUID

from ai_meeting_companion.config import ConfigError, load_settings
from ai_meeting_companion.session.export import export_markdown
from ai_meeting_companion.session.store import SessionStore, SqlAlchemySessionStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai_meeting_companion")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="start a meeting session")
    run.add_argument("--title", help="name for this session")
    run.add_argument("--no-audio", action="store_true", help="disable audio capture")
    run.add_argument("--no-screen", action="store_true", help="disable the screenshot hotkey")
    run.add_argument("--no-overlay", action="store_true", help="terminal only, no overlay window")

    sub.add_parser("sessions", help="list past sessions")
    sub.add_parser("devices", help="list microphones and the meeting-audio output device")

    export = sub.add_parser("export", help="export a session as Markdown")
    export.add_argument("session", help="session id (or unique prefix)")
    export.add_argument("-o", "--output", help="write to this file instead of stdout")
    return parser


def _resolve(store: SessionStore, ident: str) -> UUID:
    try:
        return UUID(ident)
    except ValueError:
        matches = [t.id for t in store.list_threads(500) if str(t.id).startswith(ident)]
        if len(matches) != 1:
            raise SystemExit(f"session {ident!r} matched {len(matches)} sessions")
        return matches[0]


def _print_devices() -> int:
    import sounddevice as sd

    from ai_meeting_companion.agents.perception.audio.capture import list_input_devices

    default_in = sd.default.device[0]
    print("Microphones (set AUDIO_MIC_DEVICE to a number or part of a name):")
    for index, name, api in list_input_devices():
        print(f"  [{index}] {name}  ({api}){'   <- default' if index == default_in else ''}")
    try:
        import pyaudiowpatch as pyaudio

        pa = pyaudio.PyAudio()
        try:
            out = pa.get_device_info_by_index(pa.get_host_api_info_by_type(pyaudio.paWASAPI)["defaultOutputDevice"])
            print(f"\nMeeting audio is captured from the default output device: {out['name']}")
        finally:
            pa.terminate()
    except Exception as exc:  # informational only
        print(f"\nCould not query the output device: {exc}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        settings = load_settings(require_api_key=args.command == "run")
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        if getattr(sys, "frozen", False):  # no console in the exe
            from ai_meeting_companion.ui.fatal import show_error

            show_error("AI Meeting Companion - configuration", str(exc))
        return 2

    if args.command == "devices":
        return _print_devices()

    store = SqlAlchemySessionStore(settings.db)
    try:
        if args.command == "run":
            from ai_meeting_companion.agents.factory import build_agents, load_docs, speech_terms
            from ai_meeting_companion.core.orchestrator import Orchestrator

            docs = load_docs(settings)
            terms = speech_terms(settings, docs)
            print(f"Speech vocabulary: {', '.join(terms) if terms else 'none (add terms to context files or WHISPER_HOTWORDS)'}")
            if not args.no_audio:
                mic = f"ON ({settings.audio_mic_device or 'default device'})" if settings.audio_mic else "OFF - your own voice will not be heard; set AUDIO_MIC=true in .env"
                print(f"Audio: meeting audio (loopback) ON, microphone {mic}, speech model {settings.whisper_model}")
            overlay = not args.no_overlay
            build = lambda bus, memory: build_agents(  # noqa: E731
                settings, bus, memory, audio=not args.no_audio, screen=not args.no_screen, terminal=not overlay, docs=docs
            )
            print(f"Context files: {', '.join(docs.files) if docs else 'none (add resume/notes to ./' + settings.context_dir + ')'}")
            if overlay:
                from ai_meeting_companion.ui.app import run_overlay

                print(
                    f"Overlay running. Hotkeys: show/hide {settings.overlay_toggle_hotkey}, "
                    f"suggest answer {settings.suggest_hotkey}, type {settings.overlay_focus_hotkey}, click-through {settings.overlay_clickthrough_hotkey}, quit {settings.overlay_quit_hotkey}"
                    + (f", screenshot {settings.hotkey}" if not args.no_screen else "")
                )
                thread_id = run_overlay(settings, store, build, title=args.title)
            else:
                print("Session running. Type a question and press Enter to chat, /suggest to send what was heard to the Conversor; Ctrl+C to stop.")
                if not args.no_screen:
                    print(f"Screenshot hotkey: {settings.hotkey}")
                thread_id = Orchestrator(store, build, title=args.title).run_until_interrupted()
            print(f"\nSession saved: {thread_id}")
        elif args.command == "sessions":
            for t in store.list_threads():
                print(f"{t.id}  {t.created_at:%Y-%m-%d %H:%M}  {t.status:<6}  {t.message_count:>4} msgs  {t.title or ''}")
        elif args.command == "export":
            markdown = export_markdown(store, _resolve(store, args.session))
            if args.output:
                Path(args.output).write_text(markdown, encoding="utf-8")
                print(f"Wrote {args.output}")
            else:
                print(markdown)
    finally:
        store.close()
    return 0
