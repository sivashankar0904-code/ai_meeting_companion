from __future__ import annotations

import re
from collections import Counter

_TOKEN = re.compile(r"[A-Za-z](?:[A-Za-z0-9+#./\-]*[A-Za-z0-9+#])?")
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
_CAMEL_OR_ACRONYM = re.compile(r"[a-z][A-Z]|[A-Z]{2,}")
_MIXED = re.compile(r"[A-Za-z][0-9]|[0-9][A-Za-z]|[+#./]")


def extract_terms(text: str, limit: int = 40) -> list[str]:
    """Words a speech recogniser would probably misspell, found in the user's own text.

    No word lists: a token counts if its *shape* is unusual (CamelCase, ACRONYMS, letters mixed
    with digits or symbols such as ``Node.js``/``C++``) or if it is a capitalised word in the
    middle of a sentence that is never written in lower case (names of people, companies,
    products, places). Most frequent first.
    """
    counts: Counter[str] = Counter()
    first_seen: dict[str, int] = {}
    lowercase_words: set[str] = set()
    proper: set[str] = set()

    for sentence in _SENTENCE.split(text):
        for position, match in enumerate(_TOKEN.finditer(sentence)):
            token = match.group()
            if token.islower():
                lowercase_words.add(token)
                continue
            shaped = bool(_CAMEL_OR_ACRONYM.search(token) or _MIXED.search(token))
            capitalised = token[0].isupper() and token[1:].islower()
            if shaped or (capitalised and position > 0):
                if capitalised and not shaped:
                    proper.add(token)
                counts[token] += 1
                first_seen.setdefault(token, len(first_seen))

    def keep(token: str) -> bool:
        return token not in proper or token.lower() not in lowercase_words

    ranked = sorted((t for t in counts if keep(t) and len(t) >= 2), key=lambda t: (-counts[t], first_seen[t]))
    return ranked[:limit]


def merge_terms(*groups: list[str]) -> list[str]:
    """Combine term lists, dropping case-insensitive duplicates and keeping order."""
    seen: set[str] = set()
    merged: list[str] = []
    for group in groups:
        for term in group:
            key = term.lower()
            if term and key not in seen:
                seen.add(key)
                merged.append(term)
    return merged
