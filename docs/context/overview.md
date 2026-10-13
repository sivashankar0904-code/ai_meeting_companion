# Overview

A headless pipeline of cooperating agents (PyQt6 overlay comes later):

1. Audio: capture -> transcribe (faster-whisper) -> **Conversor** specialist
2. Screen: hotkey screenshot -> OCR (Tesseract) -> **Screen Analyzer** specialist
3. Manual typed input -> **Chat** specialist
4. A session logger records every event per meeting in PostgreSQL for later reference

## Decisions
- LangChain (`langchain-anthropic`) with the Claude API only. No LM Studio.
- Keys and DB settings come from `.env`.
- Screenshot is triggered by a global hotkey.
- PostgreSQL for session logging.
- Headless first; overlay UI later.

## Specialist agents
| Agent | Input event | Default model | Job |
|---|---|---|---|
| Conversor | `transcript` (buffered; model called only on `suggest_request`) | `claude-haiku-4-5-20251001` | Identify interviewer vs interviewee, track roles, suggest an answer when the interviewer asks a question. |
| Screen Analyzer | `screen_text` | `claude-sonnet-5-5` | Work out what problem is on screen, then solve it. |
| Chat | `user_message` | `claude-sonnet-5-5` | Manual chatbot; also sees recent transcript and screen text. |

System audio has no diarization, so the Conversor infers roles from content. When loopback and mic are captured as separate streams, each transcript chunk carries a `channel` (`loopback`/`mic`) hint.

## Out of scope for v1
True speaker diarization, other LLM providers, LangGraph.
