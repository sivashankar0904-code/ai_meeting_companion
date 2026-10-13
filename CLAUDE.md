# AI Meeting Companion

Windows app that listens to a meeting, reads the screen, and suggests answers through specialist LLM agents. Everything is logged to PostgreSQL. Full project context is imported below and loads every session.

@docs/context/overview.md
@docs/context/architecture.md
@docs/context/database.md
@docs/context/configuration.md
@docs/context/conventions.md
@docs/context/status.md

## Standing rules
- Never open or read `.env` files. Use `.env.example` for the list of keys.
- Postgres is already running in WSL docker. Do not add docker files or docker steps.
- Keep `docs/context/status.md` current after each milestone.
