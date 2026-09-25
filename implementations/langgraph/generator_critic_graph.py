"""
LangGraph reference implementation of the generator-critic pattern.

Same loop as implementations/raw_api/generator_critic.py, expressed as an
explicit graph instead of a while-loop: generate -> critique -> a conditional
edge back to generate (revise) or to END. Compare this file to the raw_api
one directly -- the generator/critic calls and the stopping conditions are
identical, only the control-flow mechanism differs. That's the point: a
framework doesn't change what the pattern *is*, it changes how you express
and inspect the control flow (LangGraph gives you a visualizable graph and a
built-in recursion guard; the raw loop gives you full visibility with no
dependency).

Run:
    python implementations/langgraph/generator_critic_graph.py

Requires ANTHROPIC_API_KEY in your environment (see .env.example) and
`pip install langgraph` (see requirements.txt).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langgraph.graph import END, StateGraph

from shared.critique import Critique
from shared.display import print_critique, print_section
from shared.llm_client import (
    DEFAULT_CRITIC_MODEL,
    DEFAULT_GENERATOR_MODEL,
    TokenBudget,
    complete_structured,
    complete_text,
    extract_code_block,
)

TASK = """Write a Python function `parse_log_line(line: str) -> dict | None` that
parses a single Apache-style access log line (Common Log Format) into a dict
with keys: ip, timestamp, method, path, status, bytes. It must not raise on
malformed input -- return None instead. Include type hints and a docstring."""

MAX_ITERATIONS = 4
QUALITY_THRESHOLD = 85
TOKEN_BUDGET = 200_000

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


class GraphState(TypedDict):
    code: Optional[str]
    critique: Optional[Critique]
    iteration: int
    budget: TokenBudget


def generate_node(state: GraphState) -> dict:
    prior_code = state["code"]
    crit = state["critique"]
    if prior_code is None:
        user = f"Task:\n{TASK}"
    else:
        issues = "\n".join(f"- {issue}" for issue in crit.issues)
        user = (
            f"Task:\n{TASK}\n\n"
            f"Your previous attempt:\n```python\n{prior_code}\n```\n\n"
            f"An independent reviewer found these issues:\n{issues}\n\n"
            "Revise the function to address every issue."
        )
    text, usage = complete_text(DEFAULT_GENERATOR_MODEL, GENERATOR_SYSTEM, user)
    state["budget"].record(usage)  # mutated in place; same object flows through state
    code = extract_code_block(text)
    iteration = state["iteration"] + 1

    print_section(f"Iteration {iteration}: generate")
    print(code)
    return {"code": code, "iteration": iteration}


def critique_node(state: GraphState) -> dict:
    user = f"Task:\n{TASK}\n\nCandidate implementation:\n```python\n{state['code']}\n```"
    crit, usage = complete_structured(DEFAULT_CRITIC_MODEL, CRITIC_SYSTEM, user, Critique)
    state["budget"].record(usage)

    print_section(f"Iteration {state['iteration']}: critique")
    print_critique(crit)
    return {"critique": crit}


def route_after_critique(state: GraphState) -> str:
    """The structural stopping logic lives here, in code the model can't
    influence -- not in a prompt asking the generator to "stop when done"."""
    crit = state["critique"]
    if crit.verdict == "pass" or crit.score >= QUALITY_THRESHOLD:
        print(f"\nStopping: quality threshold met after {state['iteration']} iteration(s).")
        return "done"
    if state["budget"].exceeded():
        print(f"\nStopping: token budget exhausted after {state['iteration']} iteration(s).")
        return "done"
    if state["iteration"] >= MAX_ITERATIONS:
        print(f"\nStopping: hit max_iterations={MAX_ITERATIONS} without reaching threshold.")
        return "done"
    return "revise"


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("generate", generate_node)
    graph.add_node("critique", critique_node)
    graph.set_entry_point("generate")
    graph.add_edge("generate", "critique")
    graph.add_conditional_edges(
        "critique",
        route_after_critique,
        {"revise": "generate", "done": END},
    )
    return graph.compile()


def run() -> None:
    app = build_graph()
    initial_state: GraphState = {
        "code": None,
        "critique": None,
        "iteration": 0,
        "budget": TokenBudget(max_total_tokens=TOKEN_BUDGET),
    }
    # Belt-and-suspenders: even if route_after_critique had a bug that never
    # returned "done", LangGraph raises GraphRecursionError past this limit.
    final_state = app.invoke(
        initial_state, config={"recursion_limit": MAX_ITERATIONS * 3 + 5}
    )

    print_section("Final result")
    print(final_state["code"])
    budget = final_state["budget"]
    print(f"\nTotal tokens spent: {budget.spent_tokens} (~${budget.total_cost_usd:.4f})")


if __name__ == "__main__":
    run()
