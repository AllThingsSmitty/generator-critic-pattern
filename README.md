# Generator-Critic Pattern

Generator-critic (also called Reflection, or Evaluator-Optimizer) runs two
roles in a loop. A **generator** produces an output, a **critic** evaluates
it independently, and the generator revises based on that critique. The
loop stops when the critic passes the output, or when it hits a hard limit
like max iterations or a token budget.

```
task -> generate -> critique -> pass? -> done
              ^                  |
              |__________________| (revise, verdict = "revise")
```

That's the whole idea, and it's been explained plenty of times already.
What usually gets skipped is what actually breaks when you build one of
these for real. That's what this repo covers.

## What's here

`implementations/` has two runnable reference implementations of the loop
above: one using the raw Anthropic API with no framework, and one in
LangGraph expressing the same loop as an explicit graph.
[implementations/README.md](implementations/README.md) compares them side
by side.

`failure_modes/` covers four ways these loops fail in practice, each with
runnable code showing the failure and the fix:

- [`01_shallow_critique`](failure_modes/01_shallow_critique/): self-agreement, when the critic shares the generator's blind spots
- [`02_unbounded_loops`](failure_modes/02_unbounded_loops/): hard iteration caps and token-budget tracking
- [`03_diminishing_returns`](failure_modes/03_diminishing_returns/): logging quality per iteration so you can see when gains flatten out
- [`04_skippable_critic`](failure_modes/04_skippable_critic/): enforcing call order in code instead of trusting the LLM to follow instructions

`decision_guide/` walks through when to reach for single-model
self-critique, separate-model critique, or a tool-grounded critique (a
linter, compiler, or schema validator), with rough cost/latency/quality
tradeoffs.

## Running the examples

Needs Python 3.10+ (the pinned `anthropic` SDK version requires it).

```bash
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY
python implementations/raw_api/generator_critic.py
```

Every script under `implementations/` and `failure_modes/` runs directly
(`python path/to/script.py`) and makes real API calls. Each one prints total
tokens spent and estimated cost when it finishes. Check
[implementations/README.md](implementations/README.md) for what that costs
in practice.
