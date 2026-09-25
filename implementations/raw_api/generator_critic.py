"""
Raw Anthropic API reference implementation of the generator-critic pattern.

No framework, no magic: an explicit loop that alternates between a generator
call and an independent critic call until the critic passes the output, a
quality threshold is met, or a hard iteration cap is hit. This is the pattern
in its simplest form -- every other example in this repo (LangGraph, the
failure-mode demos) is a variation on this same loop.

Run:
    python implementations/raw_api/generator_critic.py

Requires ANTHROPIC_API_KEY in your environment (see .env.example).
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

TASK = """Write a Python function `parse_log_line(line: str) -> dict | None` that
parses a single Apache-style access log line (Common Log Format) into a dict
with keys: ip, timestamp, method, path, status, bytes. It must not raise on
malformed input -- return None instead. Include type hints and a docstring."""

MAX_ITERATIONS = 4
QUALITY_THRESHOLD = 85  # critic score out of 100, independent of verdict
TOKEN_BUDGET = 200_000  # hard cap across the whole loop -- see failure_modes/02

GENERATOR_SYSTEM = (
    "You are a senior Python engineer. Produce only the function code "
    "requested, in a single ```python code block. No prose before or after."
)

CRITIC_SYSTEM = (
    "You are an independent code reviewer. You did not write this code and "
    "have no stake in defending it. Evaluate strictly against the task "
    "specification: correctness, edge cases, and adherence to the stated "
    "contract. Be specific -- vague praise is not useful feedback. A "
    "verdict of 'pass' means you would ship this without further changes."
)


def generate(task: str, prior_code: str | None, critique: Critique | None) -> tuple[str, Usage]:
    if prior_code is None:
        user = f"Task:\n{task}"
    else:
        issues = "\n".join(f"- {issue}" for issue in critique.issues)
        user = (
            f"Task:\n{task}\n\n"
            f"Your previous attempt:\n```python\n{prior_code}\n```\n\n"
            f"An independent reviewer found these issues:\n{issues}\n\n"
            "Revise the function to address every issue."
        )
    text, usage = complete_text(DEFAULT_GENERATOR_MODEL, GENERATOR_SYSTEM, user)
    return extract_code_block(text), usage


def critique(task: str, code: str) -> tuple[Critique, Usage]:
    user = f"Task:\n{task}\n\nCandidate implementation:\n```python\n{code}\n```"
    return complete_structured(DEFAULT_CRITIC_MODEL, CRITIC_SYSTEM, user, Critique)


def run() -> None:
    budget = TokenBudget(max_total_tokens=TOKEN_BUDGET)
    code: str | None = None
    crit: Critique | None = None

    for iteration in range(1, MAX_ITERATIONS + 1):
        print_section(f"Iteration {iteration}: generate")
        code, gen_usage = generate(TASK, code, crit)
        budget.record(gen_usage)
        print(code)

        print_section(f"Iteration {iteration}: critique")
        crit, crit_usage = critique(TASK, code)
        budget.record(crit_usage)
        print_critique(crit)

        if crit.verdict == "pass" or crit.score >= QUALITY_THRESHOLD:
            print(f"\nStopping: quality threshold met after {iteration} iteration(s).")
            break
        if budget.exceeded():
            print(f"\nStopping: token budget exhausted after {iteration} iteration(s).")
            break
    else:
        print(f"\nStopping: hit max_iterations={MAX_ITERATIONS} without reaching threshold.")

    print_section("Final result")
    print(code)
    print(f"\nTotal tokens spent: {budget.spent_tokens} (~${budget.total_cost_usd:.4f})")


if __name__ == "__main__":
    run()
