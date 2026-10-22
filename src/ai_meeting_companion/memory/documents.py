from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

EXTENSIONS = {".md"}
MAX_CHARS = 30_000  # total across all files; keeps the system prompt (and cost) bounded


@dataclass(frozen=True)
class ContextDocs:
    text: str = ""
    files: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.text)


def load_context_docs(directory: Path, max_chars: int = MAX_CHARS) -> ContextDocs:
    """Read the user's own background files (resume, job description, notes).

    Every .md file in ``directory`` is included, in name order. ``README.md`` and
    files starting with ``_`` are skipped. A missing folder just means no context.
    """
    if not directory.is_dir():
        return ContextDocs()

    sections: list[str] = []
    names: list[str] = []
    remaining = max_chars
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() not in EXTENSIONS or path.name.lower() == "readme.md" or path.name.startswith("_"):
            continue
        body = path.read_text(encoding="utf-8", errors="replace").strip()
        if not body:
            continue
        if len(body) > remaining:
            log.warning("context file %s truncated (limit %d characters in total)", path.name, max_chars)
            body = body[:remaining]
        sections.append(f"### {path.name}\n{body}")
        names.append(path.name)
        remaining -= len(body)
        if remaining <= 0:
            break
    return ContextDocs(text="\n\n".join(sections), files=tuple(names))
