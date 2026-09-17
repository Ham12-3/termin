"""get_vitamin_info: what a vitamin or mineral does, where to find it and how much is enough."""

from __future__ import annotations

import re
from functools import cache

from vitaagent.tools import needs
from vitaagent.tools.data_loader import build_index, find_entry, load_json, normalise, suggest

NUTRIENTS_FILE = "nutrients.json"

# Intakes are shown for these typical adults. Milestone 4 uses the saved profile instead.
TYPICAL_ADULTS = (("male", 30), ("female", 30))

SIGNS_NOTE = (
    "These signs can have many other causes. Only a GP can say whether levels are low, "
    "usually with a blood test."
)

SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_vitamin_info",
        "description": (
            "Look up a vitamin or mineral: what it does, signs of low levels, best food sources, "
            "the NHS daily reference intake for adults, the safe upper limit and NHS advice. "
            "Covers vitamins A, B1, B2, B3, B6, B9 (folate), B12, C, D, E and K, plus iron, "
            "calcium, magnesium, zinc and potassium."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The vitamin or mineral, e.g. 'vitamin D', 'B12', 'folic acid', 'iron'.",
                }
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    },
}


def get_vitamin_info(name: str) -> dict:
    nutrients = _nutrients()
    nutrient_id = _find(name)
    if nutrient_id is None:
        return {
            "error": f"I don't have information about '{name}'.",
            "did_you_mean": [nutrients[i]["name"] for i in suggest(name, _index())],
            "available": [nutrient["name"] for nutrient in nutrients.values()],
        }

    nutrient = nutrients[nutrient_id]
    result = {
        "name": nutrient["name"],
        "type": nutrient["type"],
        "what_it_does": nutrient["what_it_does"],
        "signs_of_low_levels": nutrient["signs_of_low_levels"],
        "signs_note": SIGNS_NOTE,
        "best_food_sources": nutrient["food_sources"],
        "daily_reference_intake": _typical_adult_intakes(nutrient_id, nutrient["unit"]),
        "safe_upper_limit": _adult_upper_limit(nutrient_id, nutrient["unit"]),
        "nhs_advice": nutrient["advice"],
        "sources": nutrient["sources"],
    }
    if note := needs.intake_note(nutrient_id):
        result["intake_note"] = note
    return result


def _find(name: str) -> str | None:
    """Match the name as typed, then without a leading 'vitamin'/'vit' ('Vit B-12' -> 'b12')."""
    index = _index()
    return find_entry(name, index) or index.get(re.sub(r"^(vitamin|vit)", "", normalise(name)))


def _typical_adult_intakes(nutrient_id: str, unit: str) -> list[dict]:
    rows = []
    for sex, age in TYPICAL_ADULTS:
        group = needs.find_group(age, sex)
        rows.append({"group": group["label"], "amount": group["intakes"][nutrient_id], "unit": unit})
    return rows


def _adult_upper_limit(nutrient_id: str, unit: str) -> dict:
    limit = needs.upper_limit_for(nutrient_id, age=30)
    return {**limit, "unit": unit} if limit["amount"] is not None else limit


def _nutrients() -> dict:
    return load_json(NUTRIENTS_FILE)["nutrients"]


@cache
def _index() -> dict[str, str]:
    return build_index(_nutrients())
