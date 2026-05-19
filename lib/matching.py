"""Map LLM-extracted lines to canonical genera; flag typos/unknowns."""

import re
from difflib import get_close_matches

from .genera import CANONICAL_GENERA, CANONICAL_SET


def _clean_token(line: str) -> str:
    """Pull the first alphabetic token from a line (strips bullets, asterisks, etc.)."""
    line = line.strip().lstrip("-*•·").strip()
    # Take only first word, drop trailing punctuation
    m = re.match(r"([A-Za-z]+)", line)
    if not m:
        return ""
    token = m.group(1)
    # Normalize to Title case (Genera are capitalized)
    return token[:1].upper() + token[1:].lower()


def match_extraction(lines: list[str]) -> dict:
    """
    Given raw LLM output lines, return:
        {
            "present": set[str],   # canonical genera detected
            "unknown": list[dict], # {"raw": str, "suggestion": str | None}
        }
    """
    present: set[str] = set()
    unknown: list[dict] = []
    seen_raw: set[str] = set()

    for line in lines:
        token = _clean_token(line)
        if not token or token in seen_raw:
            continue
        seen_raw.add(token)

        if token in CANONICAL_SET:
            present.add(token)
        else:
            suggestion = None
            matches = get_close_matches(token, CANONICAL_GENERA, n=1, cutoff=0.8)
            if matches:
                suggestion = matches[0]
            unknown.append({"raw": token, "suggestion": suggestion})

    return {"present": present, "unknown": unknown}
