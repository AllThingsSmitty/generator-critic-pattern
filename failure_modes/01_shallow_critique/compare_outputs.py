"""
Runs one generated candidate through all three critic variants in this
directory and prints a side-by-side comparison, so the difference in what
each catches is visible directly in output rather than asserted in prose.

Run:
    python failure_modes/01_shallow_critique/compare_outputs.py

Note: LLM outputs are stochastic. This is a real, reproducible-in-aggregate
tendency, not a guaranteed outcome on every single run -- if one run doesn't
show the gap, re-run it or increase the sample size yourself.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import different_model_critic
import same_model_critic
import separate_prompt_critic
from common import generate_candidate

from shared.display import print_section

CRITICS = [
    ("same-model, shallow prompt", same_model_critic.critique),
    ("same-model, adversarial prompt", separate_prompt_critic.critique),
    ("different-model, shallow prompt", different_model_critic.critique),
]

INJECTION_KEYWORDS = ("inject", "sanitiz", "parameteriz")


def flags_injection(issues: list[str]) -> bool:
    return any(kw in issue.lower() for issue in issues for kw in INJECTION_KEYWORDS)


def run() -> None:
    print_section("Generate (once -- all three critics evaluate this same artifact)")
    code, _ = generate_candidate()
    print(code)

    results = []
    for label, critique_fn in CRITICS:
        crit, _ = critique_fn(code)
        results.append((label, crit.verdict, crit.score, flags_injection(crit.issues), len(crit.issues)))

    print_section("Comparison")
    header = f"{'Critic':38} {'Verdict':8} {'Score':6} {'Flagged injection':18} {'#Issues'}"
    print(header)
    print("-" * len(header))
    for label, verdict, score, flagged, n_issues in results:
        print(f"{label:38} {verdict:8} {score:<6} {str(flagged):18} {n_issues}")

    shallow_same_flagged = results[0][3]
    different_model_flagged = results[2][3]
    if not shallow_same_flagged and different_model_flagged:
        print(
            "\nThis run reproduced the failure mode: the same-model shallow "
            "critic missed the SQL injection; the different-model critic, "
            "given the identical shallow prompt, caught it anyway."
        )
    elif not shallow_same_flagged and not different_model_flagged:
        print(
            "\nNeither shallow critic flagged the injection this run -- a "
            "reminder that 'different model' decorrelates the blind spot, "
            "it doesn't guarantee catching it. See decision_guide/README.md."
        )


if __name__ == "__main__":
    run()
