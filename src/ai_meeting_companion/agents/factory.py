from __future__ import annotations

from ai_meeting_companion.agents.perception.audio.agent import AudioAgent
from ai_meeting_companion.agents.perception.audio.capture import LoopbackSource, MicSource
from ai_meeting_companion.agents.perception.audio.transcriber import WhisperTranscriber
from ai_meeting_companion.agents.perception.manual_input import ManualInputAgent
from ai_meeting_companion.agents.perception.screen.agent import ScreenAgent
from ai_meeting_companion.agents.perception.screen.capture import grab_screen
from ai_meeting_companion.agents.perception.screen.hotkey import make_hotkey_listener
from ai_meeting_companion.agents.perception.screen.ocr import make_ocr
from ai_meeting_companion.agents.specialists.chat import ChatAgent
from ai_meeting_companion.agents.specialists.conversor import Conversor
from ai_meeting_companion.agents.specialists.screen_analyzer import ScreenAnalyzer
from ai_meeting_companion.config import PROJECT_ROOT, Settings, resolve_tesseract
from ai_meeting_companion.core.agent import BaseAgent
from ai_meeting_companion.core.bus import Bus
from ai_meeting_companion.llm.models import make_chat_model
from ai_meeting_companion.memory.documents import ContextDocs, load_context_docs
from ai_meeting_companion.memory.session_memory import SessionMemory
from ai_meeting_companion.memory.vocabulary import extract_terms, merge_terms
from ai_meeting_companion.ui.console import ConsolePrinter


def load_docs(settings: Settings) -> ContextDocs:
    """The user's resume / job description / notes from the context folder."""
    directory = PROJECT_ROOT / settings.context_dir
    return load_context_docs(directory)


def speech_terms(settings: Settings, docs: ContextDocs) -> list[str]:
    """Names and jargon to help speech recognition: the user's own terms plus those found in their context files."""
    configured = [t for t in settings.whisper_hotwords.replace(",", " ").split() if t]
    learned = extract_terms(docs.text) if settings.whisper_auto_vocab and docs else []
    return merge_terms(configured, learned)


def build_agents(
    settings: Settings,
    bus: Bus,
    memory: SessionMemory,
    *,
    audio: bool = True,
    screen: bool = True,
    terminal: bool = True,
    docs: ContextDocs | None = None,
) -> list[BaseAgent]:
    key = settings.anthropic_api_key
    docs = docs if docs is not None else load_docs(settings)
    background = docs.text
    agents: list[BaseAgent] = [
        Conversor(
            bus, make_chat_model(settings.conversor_model, key, max_tokens=1024), settings.conversor_model,
            background=background, memory=memory, memory_chars=settings.session_memory_chars,
        ),
        ScreenAnalyzer(
            bus, make_chat_model(settings.screen_model, key, max_tokens=2048), settings.screen_model,
            memory=memory, memory_chars=settings.session_memory_chars,
        ),
        ChatAgent(
            bus, make_chat_model(settings.chat_model, key, max_tokens=2048), settings.chat_model,
            background=background, memory=memory, memory_chars=settings.session_memory_chars,
        ),
    ]
    if terminal:  # console output and typed input; the overlay replaces both
        agents += [ConsolePrinter(bus), ManualInputAgent(bus)]
    if audio:
        sources = [LoopbackSource(settings.audio_chunk_secs)]
        if settings.audio_mic:
            sources.append(MicSource(settings.audio_chunk_secs, settings.audio_mic_device))
        agents.append(AudioAgent(bus, sources, WhisperTranscriber(settings.whisper_model, speech_terms(settings, docs), settings.whisper_prompt, settings.whisper_device)))
    if screen:
        agents.append(
            ScreenAgent(
                bus,
                grab_screen,
                make_ocr(resolve_tesseract(settings.tesseract_cmd)),
                lambda cb: make_hotkey_listener(settings.hotkey, cb),
            )
        )
    return agents
