import pytest
from pydantic import ValidationError

from shared.critique import Critique


def test_valid_critique_round_trips_fields() -> None:
    critique = Critique(
        score=85,
        issues=["missing docstring"],
        verdict="pass",
        reasoning="Clean and correct, one minor style nit.",
    )
    assert critique.score == 85
    assert critique.issues == ["missing docstring"]
    assert critique.verdict == "pass"


def test_issues_defaults_to_empty_list() -> None:
    critique = Critique(score=100, verdict="pass", reasoning="No issues found.")
    assert critique.issues == []


@pytest.mark.parametrize("score", [-1, 101])
def test_score_out_of_range_rejected(score: int) -> None:
    with pytest.raises(ValidationError):
        Critique(score=score, verdict="pass", reasoning="x")


def test_invalid_verdict_rejected() -> None:
    with pytest.raises(ValidationError):
        Critique(score=50, verdict="maybe", reasoning="x")


def test_missing_required_field_rejected() -> None:
    with pytest.raises(ValidationError):
        Critique(score=50, verdict="pass")
