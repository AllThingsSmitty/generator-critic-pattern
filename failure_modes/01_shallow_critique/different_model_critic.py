"""
Failure mode: self-agreement / shallow critique -- fix.

Uses the exact same shallow, non-adversarial critique prompt as
same_model_critic.py -- the only variable changed is the critic model itself
(DEFAULT_INDEPENDENT_CRITIC_MODEL instead of DEFAULT_GENERATOR_MODEL, the
model that wrote the code). This isolates "different model" as the fix,
rather than conflating it with "better prompt" (that's
separate_prompt_critic.py). A different model trained with different
data/RLHF doesn't necessarily share the generator's blind spots, so it has a
real chance of flagging what the generator missed -- even without being told
to look for anything in particular.

This is not a guarantee. Different models can still share a blind spot (e.g.
both may default to prioritizing "does it run" over "is it safe" unless
asked). It decorrelates the failure, it doesn't eliminate it -- see
decision_guide/README.md for when a tool-grounded check (a linter, a static
analyzer) is the more reliable fix than any LLM critic, same-model or not.

Run standalone:
    python failure_modes/01_shallow_critique/different_model_critic.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common import TASK, generate_candidate

from shared.critique import Critique
from shared.display import print_critique, print_section
from shared.llm_client import DEFAULT_INDEPENDENT_CRITIC_MODEL, Usage, complete_structured

# Deliberately identical to same_model_critic.py's prompt -- the model is
# the only thing we're changing here.
SHALLOW_CRITIC_SYSTEM = (
    "You are reviewing a piece of Python code. Check whether it correctly "
    "fulfills the task described."
)


def critique(code: str) -> tuple[Critique, Usage]:
    user = f"Task:\n{TASK}\n\nCode:\n```python\n{code}\n```"
    return complete_structured(
        DEFAULT_INDEPENDENT_CRITIC_MODEL, SHALLOW_CRITIC_SYSTEM, user, Critique
    )


if __name__ == "__main__":
    print_section("Generate")
    code, _ = generate_candidate()
    print(code)

    print_section(f"Critique ({DEFAULT_INDEPENDENT_CRITIC_MODEL}, shallow prompt)")
    crit, _ = critique(code)
    print_critique(crit)
