import pytest

from vitaagent.agent.prompts import build_system_prompt


@pytest.mark.parametrize(
    "phrase",
    [
        "not medical advice",
        "gp, pharmacist or dietitian",
        "safe upper limit",
        "very low calorie",
        "simple and easy to read",
        "never invent",
        "not a deficiency",
        "call 999",
        "eating disorder",
        "ask before saving",
    ],
)
def test_system_prompt_includes_safety_rule(phrase):
    assert phrase in build_system_prompt().lower()
