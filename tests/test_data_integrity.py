"""Checks that the data files are complete and consistent with each other."""

from numbers import Number

import pytest

from vitaagent.tools.data_loader import load_json, normalise
from vitaagent.tools.needs import upper_limit_for

NUTRIENT_IDS = {
    "vitamin_a", "vitamin_b1", "vitamin_b2", "vitamin_b3", "vitamin_b6", "vitamin_b9",
    "vitamin_b12", "vitamin_c", "vitamin_d", "vitamin_e", "vitamin_k",
    "iron", "calcium", "magnesium", "zinc", "potassium",
}  # fmt: skip

NUTRIENTS = load_json("nutrients.json")["nutrients"]
NEEDS = load_json("daily_needs.json")
GROUPS = NEEDS["groups"]


def is_positive_number(value) -> bool:
    return isinstance(value, Number) and not isinstance(value, bool) and value > 0


def is_list_of_text(value) -> bool:
    return isinstance(value, list) and len(value) > 0 and all(isinstance(v, str) and v for v in value)


def test_nutrients_file_covers_exactly_the_16_nutrients():
    assert set(NUTRIENTS) == NUTRIENT_IDS


@pytest.mark.parametrize("nutrient_id", sorted(NUTRIENT_IDS))
def test_nutrient_entry_is_complete(nutrient_id):
    nutrient = NUTRIENTS[nutrient_id]
    assert nutrient["name"]
    assert nutrient["type"] in {"vitamin", "mineral"}
    assert nutrient["unit"] in {"mg", "µg"}
    assert isinstance(nutrient["aliases"], list)
    for key in ("what_it_does", "signs_of_low_levels", "food_sources", "advice"):
        assert is_list_of_text(nutrient[key]), key
    assert nutrient["sources"]
    assert all(url.startswith("https://") for url in nutrient["sources"])


def test_names_and_aliases_are_unique_across_nutrients():
    owner = {}
    for nutrient_id, nutrient in NUTRIENTS.items():
        for label in {normalise(x) for x in (nutrient_id, nutrient["name"], *nutrient["aliases"])}:
            assert owner.setdefault(label, nutrient_id) == nutrient_id, label


def test_needs_file_names_its_standard_and_sources():
    assert "NHS" in NEEDS["standard"]
    assert NEEDS["sources"]
    assert all(source["url"].startswith("https://") for source in NEEDS["sources"])


@pytest.mark.parametrize("sex", ["male", "female"])
def test_groups_cover_every_age_from_1_without_gaps_or_overlaps(sex):
    groups = sorted((g for g in GROUPS if g["sex"] == sex), key=lambda g: g["age_min"])
    assert groups[0]["age_min"] == 1
    for earlier, later in zip(groups, groups[1:]):
        assert later["age_min"] == earlier["age_max"] + 1
    assert groups[-1]["age_max"] is None


def test_group_ids_and_labels_are_unique():
    assert len({g["id"] for g in GROUPS}) == len(GROUPS)
    assert len({g["label"] for g in GROUPS}) == len(GROUPS)


@pytest.mark.parametrize("group", GROUPS, ids=lambda g: g["id"])
def test_group_has_an_intake_entry_for_every_nutrient(group):
    assert set(group["intakes"]) == NUTRIENT_IDS
    for nutrient_id, amount in group["intakes"].items():
        if amount is None:
            assert nutrient_id in NEEDS["intake_notes"], f"{nutrient_id} has no figure and no note"
        else:
            assert is_positive_number(amount), nutrient_id


def test_adults_have_a_figure_for_every_nutrient():
    for group in (g for g in GROUPS if g["age_min"] >= 19):
        assert None not in group["intakes"].values(), group["id"]


def test_upper_limit_entries_are_complete_and_do_not_overlap():
    assert set(NEEDS["upper_limits"]) <= NUTRIENT_IDS
    for nutrient_id, limits in NEEDS["upper_limits"].items():
        for limit in limits:
            assert is_positive_number(limit["amount"]), nutrient_id
            assert limit["applies_to"] and limit["note"], nutrient_id
        ranges = sorted((l["age_min"], l["age_max"]) for l in limits)
        for (_, earlier_max), (later_min, _) in zip(ranges, ranges[1:]):
            assert earlier_max is not None and later_min > earlier_max, nutrient_id


def test_every_nutrient_has_an_adult_upper_limit():
    for nutrient_id in NUTRIENT_IDS:
        assert upper_limit_for(nutrient_id, age=30)["amount"] is not None, nutrient_id


@pytest.mark.parametrize("group", GROUPS, ids=lambda g: g["id"])
def test_upper_limits_are_above_daily_intakes(group):
    for nutrient_id, amount in group["intakes"].items():
        limit = upper_limit_for(nutrient_id, group["age_min"])["amount"]
        if amount is not None and limit is not None:
            assert limit > amount, nutrient_id


def test_pregnancy_extras_use_known_nutrients():
    pregnancy = NEEDS["pregnancy"]
    assert set(pregnancy["extra"]) <= NUTRIENT_IDS
    assert all(is_positive_number(amount) for amount in pregnancy["extra"].values())
    assert set(pregnancy["extra_notes"]) <= set(pregnancy["extra"])
    assert is_list_of_text(pregnancy["notes"])
