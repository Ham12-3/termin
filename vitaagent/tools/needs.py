"""Daily reference intakes and safe upper limits, read from data/daily_needs.json.

Milestone 3 adds the get_daily_needs tool to this module.
"""

from __future__ import annotations

from vitaagent.tools.data_loader import load_json

NEEDS_FILE = "daily_needs.json"


def _in_age_range(age: int, entry: dict) -> bool:
    return entry["age_min"] <= age and (entry["age_max"] is None or age <= entry["age_max"])


def find_group(age: int, sex: str) -> dict | None:
    """The life-stage group for this age and sex, or None if not covered (e.g. under 1)."""
    for group in load_json(NEEDS_FILE)["groups"]:
        if group["sex"] == sex and _in_age_range(age, group):
            return group
    return None


def intake_note(nutrient_id: str) -> str | None:
    """Extra context for intakes that aren't standard UK RNIs (e.g. vitamins E and K)."""
    return load_json(NEEDS_FILE)["intake_notes"].get(nutrient_id)


def upper_limit_for(nutrient_id: str, age: int) -> dict:
    """The NHS safe upper limit for this age: {amount, applies_to, note}.

    `amount` is None when the NHS gives no limit for this age group.
    """
    data = load_json(NEEDS_FILE)
    for limit in data["upper_limits"].get(nutrient_id, []):
        if _in_age_range(age, limit):
            return {key: value for key, value in limit.items() if key not in ("age_min", "age_max")}
    return {"amount": None, "note": data["no_upper_limit_note"]}
