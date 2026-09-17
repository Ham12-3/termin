"""Load the JSON data files and match user-typed names to entries."""

from __future__ import annotations

import difflib
import json
import re
from functools import cache

from vitaagent.config import DATA_DIR


@cache
def load_json(filename: str) -> dict:
    with (DATA_DIR / filename).open(encoding="utf-8") as file:
        return json.load(file)


def normalise(text: str) -> str:
    """Lowercase and keep only letters and digits: 'Vit. B-12' -> 'vitb12'."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def build_index(entries: dict[str, dict]) -> dict[str, str]:
    """Map each entry's normalised id, name and aliases to the entry id."""
    index = {}
    for entry_id, entry in entries.items():
        for label in (entry_id, entry["name"], *entry.get("aliases", [])):
            index[normalise(label)] = entry_id
    return index


def find_entry(query: str, index: dict[str, str]) -> str | None:
    return index.get(normalise(query))


def suggest(query: str, index: dict[str, str], limit: int = 3) -> list[str]:
    """Entry ids whose names or aliases look like `query`, best first."""
    matches = difflib.get_close_matches(normalise(query), list(index), n=limit * 3, cutoff=0.6)
    return list(dict.fromkeys(index[match] for match in matches))[:limit]
