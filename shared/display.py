"""Console output helpers shared across examples -- kept separate from
llm_client.py so scripts that don't need pretty-printing (e.g. the
compare_outputs table) don't have to pull in an unused dependency."""
from __future__ import annotations

from shared.critique import Critique


def print_section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def print_critique(critique: Critique) -> None:
    print(f"Score: {critique.score}/100  |  Verdict: {critique.verdict}")
    if critique.issues:
        print("Issues:")
        for issue in critique.issues:
            print(f"  - {issue}")
    else:
        print("Issues: none reported")
    print(f"Reasoning: {critique.reasoning}")
