"""
Failure mode: self-agreement / shallow critique.

The critic here is the *same model* that wrote the code, evaluated with a
plain "does this satisfy the task?" prompt in a fresh, independent call (no
shared conversation history -- note that independence of the call alone does
not fix this). The generator task (see common.py) doesn't mention security,
so a model that defaults to string-formatted SQL when writing the function
tends to make the same omission reviewing it: it checks "does this return
the right row for a normal username" and stops there, because that's the
same lens it used to write the code in the first place.

Run standalone:
    python failure_modes/01_shallow_critique/same_model_critic.py

Or see compare_outputs.py for a side-by-side against the other two critics.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common import TASK, generate_candidate

from shared.critique import Critique
from shared.display import print_critique, print_section
from shared.llm_client import DEFAULT_GENERATOR_MODEL, Usage, complete_structured

SHALLOW_CRITIC_SYSTEM = (
    "You are reviewing a piece of Python code. Check whether it correctly "
    "fulfills the task described."
)


def critique(code: str) -> tuple[Critique, Usage]:
    user = f"Task:\n{TASK}\n\nCode:\n```python\n{code}\n```"
    # Same model as the generator, shallow non-adversarial prompt.
    return complete_structured(DEFAULT_GENERATOR_MODEL, SHALLOW_CRITIC_SYSTEM, user, Critique)


if __name__ == "__main__":
    print_section("Generate")
    code, _ = generate_candidate()
    print(code)

    print_section("Critique (same model, shallow prompt)")
    crit, _ = critique(code)
    print_critique(crit)

    flagged = any(
        kw in issue.lower()
        for issue in crit.issues
        for kw in ("inject", "sanitiz", "parameteriz")
    )
    if not flagged:
        print(
            "\nNote: this critique did not flag SQL injection -- the classic "
            "same-model blind spot this example is demonstrating."
        )
