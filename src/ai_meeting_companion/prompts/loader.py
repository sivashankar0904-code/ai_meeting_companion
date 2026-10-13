from __future__ import annotations

from importlib import resources

from ai_meeting_companion import config


def load_prompt(name: str) -> str:
    """The text of ``prompts/<name>.md``.

    A file ``prompts/<name>.md`` placed next to the app (project folder or exe) wins over the built-in
    one, so prompts can be tuned without rebuilding the exe."""
    override = config.PROJECT_ROOT / "prompts" / f"{name}.md"
    if override.is_file():
        return override.read_text("utf-8").strip()
    return resources.files("ai_meeting_companion.prompts").joinpath(f"{name}.md").read_text("utf-8").strip()


def build_system_prompt(name: str, background: str = "") -> str:
    """``prompts/<name>.md`` + the shared-memory instructions + the user's background documents."""
    return with_background(f"{load_prompt(name)}\n\n{load_prompt('shared_memory')}", background)


def with_background(prompt: str, background: str) -> str:
    """Append the user's context documents to a system prompt (unchanged when empty)."""
    if not background.strip():
        return prompt
    return (
        f"{prompt}\n\n"
        "## Background documents provided by the user\n"
        "Treat these as facts about the user and the situation. Ground answers in them and do not "
        "contradict them.\n\n"
        f"{background.strip()}"
    )
