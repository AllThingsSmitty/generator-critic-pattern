"""
Failure mode: self-agreement / shallow critique -- partial fix #1.

Same model as the generator (still the same DEFAULT_GENERATOR_MODEL), but
the critic system prompt is adversarial and rubric-driven instead of a
generic "does this work?" ask. This catches more than same_model_critic.py's
shallow prompt does -- but it is still the same model's weights doing the
judging. If the model's blind spot is fundamental (it genuinely doesn't
associate string-formatted SQL with risk, rather than simply not having been
asked to check), a better prompt narrows the gap but doesn't close it. See
different_model_critic.py for the stronger fix, and decision_guide/README.md
for when even a different model isn't enough and you want a tool-grounded
check instead.

Run standalone:
    python failure_modes/01_shallow_critique/separate_prompt_critic.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common import TASK, generate_candidate

from shared.critique import Critique
from shared.display import print_critique, print_section
from shared.llm_client import DEFAULT_GENERATOR_MODEL, Usage, complete_structured

ADVERSARIAL_CRITIC_SYSTEM = (
    "You are a hostile senior security reviewer. Assume the code in front of "
    "you is wrong until proven otherwise. Check specifically, in order: "
    "(1) injection vulnerabilities in any database, shell, or file-path "
    "construction, (2) unhandled exceptions on malformed input, (3) resource "
    "leaks such as unclosed connections or files, (4) whether the return "
    "contract matches the spec exactly. List every issue you find, however "
    "minor. A 'pass' verdict means you would stake your reputation on this "
    "code in production."
)


def critique(code: str) -> tuple[Critique, Usage]:
    user = f"Task:\n{TASK}\n\nCode:\n```python\n{code}\n```"
    return complete_structured(DEFAULT_GENERATOR_MODEL, ADVERSARIAL_CRITIC_SYSTEM, user, Critique)


if __name__ == "__main__":
    print_section("Generate")
    code, _ = generate_candidate()
    print(code)

    print_section("Critique (same model, adversarial rubric prompt)")
    crit, _ = critique(code)
    print_critique(crit)
