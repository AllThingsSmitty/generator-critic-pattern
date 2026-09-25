"""
Failure mode: unbounded loops.

The anti-pattern (illustrative only -- do not run this):

    while True:
        code = generate(...)
        crit = critique(code)
        if crit.verdict == "pass":
            break
        # No cap on iterations, no cap on tokens spent getting here. A
        # critic that never says "pass" -- because the task is ambiguous,
        # the quality bar is miscalibrated, or the critic itself is
        # unreliable -- runs this forever, spending real money on every
        # iteration with nothing to stop it.

The fix below combines two independent caps, because either one alone is
insufficient:

- MAX_ITERATIONS caps the number of loop iterations. Insufficient alone if a
  single iteration can be arbitrarily expensive (e.g. the generator starts
  producing long, rambling output).
- TokenBudget caps cumulative tokens spent, regardless of iteration count.
  Insufficient alone if you also want a bound on call count / wall-clock
  time independent of token usage.

Both are checked every iteration; whichever trips first stops the loop, and
the reason is logged so "converged" is distinguishable from "gave up."

This example deliberately sets an almost-unreachable quality bar and a tight
token budget so you can watch the caps actually trip, instead of the loop
converging on the first try.

Run:
    python failure_modes/02_unbounded_loops/bounded_loop.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.critique import Critique
from shared.display import print_critique, print_section
from shared.llm_client import (
    DEFAULT_CRITIC_MODEL,
    DEFAULT_GENERATOR_MODEL,
    TokenBudget,
    Usage,
    complete_structured,
    complete_text,
    extract_code_block,
)

TASK = """Write a Python function `merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]`
that merges overlapping intervals and returns them sorted by start. Handle
empty input, single intervals, and fully-nested intervals."""

QUALITY_THRESHOLD = 99  # near-unreachable on purpose, to exercise the caps
MAX_ITERATIONS = 6
TOKEN_BUDGET = 12_000  # deliberately tight, so the budget cap binds first

GENERATOR_SYSTEM = (
    "You are a Python engineer. Produce only the function code requested, "
    "in a single ```python code block. No prose before or after."
)

CRITIC_SYSTEM = (
    "You are an exacting code reviewer. Only return verdict 'pass' for a "
    "genuinely exceptional, production-ready implementation with complete "
    "docstrings, type hints, and explicit handling of every edge case you "
    "can think of. Hold a very high bar."
)


def generate(prior_code: str | None, critique: Critique | None) -> tuple[str, Usage]:
    if prior_code is None:
        user = f"Task:\n{TASK}"
    else:
        issues = "\n".join(f"- {issue}" for issue in critique.issues)
        user = (
            f"Task:\n{TASK}\n\nYour previous attempt:\n```python\n{prior_code}\n```\n\n"
            f"Reviewer feedback:\n{issues}\n\nRevise to address every issue."
        )
    text, usage = complete_text(DEFAULT_GENERATOR_MODEL, GENERATOR_SYSTEM, user)
    return extract_code_block(text), usage


def critique(code: str) -> tuple[Critique, Usage]:
    user = f"Task:\n{TASK}\n\nCandidate implementation:\n```python\n{code}\n```"
    return complete_structured(DEFAULT_CRITIC_MODEL, CRITIC_SYSTEM, user, Critique)


def run() -> None:
    budget = TokenBudget(max_total_tokens=TOKEN_BUDGET)
    code: str | None = None
    crit: Critique | None = None
    stop_reason: str | None = None
    iteration = 0

    for iteration in range(1, MAX_ITERATIONS + 1):
        print_section(f"Iteration {iteration}: generate")
        code, gen_usage = generate(code, crit)
        budget.record(gen_usage)
        print(f"({len(code.splitlines())} lines) -- tokens spent: {budget.spent_tokens}/{TOKEN_BUDGET}")

        if budget.exceeded():
            stop_reason = f"token budget exhausted mid-iteration {iteration} (right after the generate call)"
            break

        print_section(f"Iteration {iteration}: critique")
        crit, crit_usage = critique(code)
        budget.record(crit_usage)
        print_critique(crit)
        print(f"Tokens spent: {budget.spent_tokens}/{TOKEN_BUDGET}")

        if crit.verdict == "pass":
            stop_reason = f"critic passed the output after {iteration} iteration(s)"
            break
        if budget.exceeded():
            stop_reason = f"token budget exhausted after iteration {iteration}"
            break
    else:
        stop_reason = f"hit hard cap MAX_ITERATIONS={MAX_ITERATIONS}"

    print_section("Stopped")
    print(f"Reason: {stop_reason}")
    print(f"Iterations run: {iteration}")
    print(f"Tokens spent: {budget.spent_tokens} (~${budget.total_cost_usd:.4f}) of {TOKEN_BUDGET} budget")
    print("\nFinal candidate:")
    print(code)


if __name__ == "__main__":
    run()
