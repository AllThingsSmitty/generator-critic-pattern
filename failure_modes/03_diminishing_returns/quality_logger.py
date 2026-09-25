"""
Failure mode: diminishing returns.

Nothing about the generator-critic loop itself knows when it's flattening --
each additional iteration can keep "refining" long after the gains have
dropped to noise, and a fixed iteration count either stops too early (if set
conservatively) or wastes calls (if set generously) because it isn't
responding to the actual quality curve.

This example runs a *fixed* number of iterations without early-stopping on a
threshold, purely to log critic score per iteration, then detects and
reports the point where gains flattened -- so you can see the curve instead
of guessing at a cutoff.

Run:
    python failure_modes/03_diminishing_returns/quality_logger.py
    python failure_modes/03_diminishing_returns/quality_logger.py --plot   # also saves a PNG (requires matplotlib)
"""
from __future__ import annotations

import argparse
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

ITERATIONS = 6  # fixed, not threshold-gated -- we want the whole curve
FLATTEN_DELTA_THRESHOLD = 2  # score-point delta below which a step counts as "flat"
FLATTEN_STREAK = 2  # consecutive flat deltas required before flagging flattening

GENERATOR_SYSTEM = (
    "You are a senior Python engineer. Produce only the function code "
    "requested, in a single ```python code block. No prose before or after."
)

CRITIC_SYSTEM = (
    "You are an independent code reviewer. Score strictly against the task "
    "specification: correctness, edge cases, code quality, and "
    "documentation. Be consistent across reviews of revised versions of the "
    "same function -- score whatever is objectively still missing, don't "
    "inflate scores just because a revision was made."
)


def generate(prior_code: str | None, critique: Critique | None) -> tuple[str, Usage]:
    if prior_code is None:
        user = f"Task:\n{TASK}"
    else:
        issues = "\n".join(f"- {issue}" for issue in critique.issues) or "(none flagged -- polish further)"
        user = (
            f"Task:\n{TASK}\n\nYour previous attempt:\n```python\n{prior_code}\n```\n\n"
            f"Reviewer feedback:\n{issues}\n\nRevise to improve the implementation."
        )
    text, usage = complete_text(DEFAULT_GENERATOR_MODEL, GENERATOR_SYSTEM, user)
    return extract_code_block(text), usage


def critique(code: str) -> tuple[Critique, Usage]:
    user = f"Task:\n{TASK}\n\nCandidate implementation:\n```python\n{code}\n```"
    return complete_structured(DEFAULT_CRITIC_MODEL, CRITIC_SYSTEM, user, Critique)


def find_flatten_point(scores: list[int]) -> int | None:
    """Return the 1-indexed iteration at which a streak of small gains was
    first detected, or None if returns never flattened within the run."""
    streak = 0
    for i in range(1, len(scores)):
        delta = scores[i] - scores[i - 1]
        if delta < FLATTEN_DELTA_THRESHOLD:
            streak += 1
            if streak >= FLATTEN_STREAK:
                return i - FLATTEN_STREAK + 2
        else:
            streak = 0
    return None


def run(make_plot: bool) -> None:
    budget = TokenBudget(max_total_tokens=500_000)
    code: str | None = None
    crit: Critique | None = None
    scores: list[int] = []

    for iteration in range(1, ITERATIONS + 1):
        print_section(f"Iteration {iteration}: generate")
        code, gen_usage = generate(code, crit)
        budget.record(gen_usage)
        print(code)

        print_section(f"Iteration {iteration}: critique")
        crit, crit_usage = critique(code)
        budget.record(crit_usage)
        print_critique(crit)
        scores.append(crit.score)

    print_section("Quality per iteration")
    prev = None
    for i, score in enumerate(scores, start=1):
        delta_str = "" if prev is None else f"  (delta {score - prev:+d})"
        print(f"  Iteration {i}: {score}/100{delta_str}")
        prev = score

    flatten_at = find_flatten_point(scores)
    print()
    if flatten_at:
        wasted_usage = budget.usage_log[2 * flatten_at :]
        wasted_tokens = sum(u.total_tokens for u in wasted_usage)
        print(
            f"Returns flattened at iteration {flatten_at}: {FLATTEN_STREAK} "
            f"consecutive deltas under {FLATTEN_DELTA_THRESHOLD} points. A "
            f"loop instrumented like this could have stopped there instead "
            f"of running all {ITERATIONS} iterations -- the iterations after "
            f"that point spent {wasted_tokens} tokens for marginal gain."
        )
    else:
        print(f"No flattening detected across {ITERATIONS} iterations at this threshold.")

    print(f"\nTotal tokens spent: {budget.spent_tokens} (~${budget.total_cost_usd:.4f})")

    if make_plot:
        save_plot(scores, flatten_at)


def save_plot(scores: list[int], flatten_at: int | None) -> None:
    import matplotlib.pyplot as plt

    iterations = list(range(1, len(scores) + 1))
    fig, ax = plt.subplots()
    ax.plot(iterations, scores, marker="o")
    if flatten_at:
        ax.axvline(flatten_at, color="red", linestyle="--", label=f"flattened at {flatten_at}")
        ax.legend()
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Critic score")
    ax.set_title("Quality per iteration")
    out_path = Path(__file__).with_name("quality_per_iteration.png")
    fig.savefig(out_path)
    print(f"\nSaved plot to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plot", action="store_true", help="save a PNG chart (requires matplotlib)")
    args = parser.parse_args()
    run(make_plot=args.plot)
