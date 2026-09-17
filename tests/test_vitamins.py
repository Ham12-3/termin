import json

import pytest

from vitaagent.tools.vitamins import get_vitamin_info


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Vitamin D", "Vitamin D"),
        ("vitamin d3", "Vitamin D"),
        ("D", "Vitamin D"),
        ("  vit. D ", "Vitamin D"),
        ("B12", "Vitamin B12"),
        ("vitamin B-12", "Vitamin B12"),
        ("cobalamin", "Vitamin B12"),
        ("folic acid", "Vitamin B9 (folate)"),
        ("FOLATE", "Vitamin B9 (folate)"),
        ("vitamin b9", "Vitamin B9 (folate)"),
        ("thiamine", "Vitamin B1 (thiamin)"),
        ("niacin", "Vitamin B3 (niacin)"),
        ("retinol", "Vitamin A"),
        ("iron", "Iron"),
        ("Calcium", "Calcium"),
        ("zinc", "Zinc"),
    ],
)
def test_finds_nutrients_by_name_or_alias(query, expected):
    assert get_vitamin_info(query)["name"] == expected


def test_returns_everything_the_agent_needs():
    info = get_vitamin_info("vitamin D")
    assert info["type"] == "vitamin"
    for key in ("what_it_does", "signs_of_low_levels", "best_food_sources", "nhs_advice", "sources"):
        assert info[key], key
    assert "other causes" in info["signs_note"]
    assert any("nhs.uk" in url for url in info["sources"])


def test_vitamin_d_intake_and_upper_limit_match_the_nhs():
    info = get_vitamin_info("vitamin D")
    assert [(row["amount"], row["unit"]) for row in info["daily_reference_intake"]] == [
        (10, "µg"),
        (10, "µg"),
    ]
    limit = info["safe_upper_limit"]
    assert (limit["amount"], limit["unit"]) == (100, "µg")
    assert limit["applies_to"]


def test_intake_is_shown_for_men_and_women():
    rows = get_vitamin_info("iron")["daily_reference_intake"]
    assert [row["amount"] for row in rows] == [8.7, 14.8]
    assert "Men" in rows[0]["group"]
    assert "Women" in rows[1]["group"]


def test_vitamin_k_explains_its_body_weight_based_figure():
    assert "body weight" in get_vitamin_info("vitamin K")["intake_note"]


def test_standard_nutrients_have_no_intake_note():
    assert "intake_note" not in get_vitamin_info("vitamin C")


def test_unknown_name_suggests_close_matches():
    result = get_vitamin_info("calcuim")
    assert "calcuim" in result["error"]
    assert "Calcium" in result["did_you_mean"]
    assert len(result["available"]) == 16


def test_unrelated_name_returns_error_without_crashing():
    result = get_vitamin_info("pizza")
    assert "error" in result
    assert isinstance(result["did_you_mean"], list)


@pytest.mark.parametrize("query", ["vitamin A", "iron", "potassium", "nonsense"])
def test_results_are_json_serialisable(query):
    json.dumps(get_vitamin_info(query), ensure_ascii=False)
