# Generator-Critic Pattern

The generator-critic pattern (also called Reflection, or Evaluator-Optimizer)
runs two roles in a loop: a **generator** produces an output, a **critic**
evaluates it independently, and the generator refines its output based on
that critique. The loop repeats until the critic passes the output or a hard
stop condition (max iterations, token budget) is reached.

```
task -> generate -> critique -> pass? -> done
              ^                  |
              |__________________| (revise, verdict = "revise")
```

That's the whole idea, and plenty has been written about it already. What's
mostly _not_ written about is what breaks when you actually build one --
that's what this repo is for.

## What's here

- **[implementations/](implementations/)** -- two runnable reference
  implementations of the loop above: a [raw Anthropic API](implementations/raw_api/generator_critic.py)
  version with no framework, and a [LangGraph](implementations/langgraph/generator_critic_graph.py)
  version expressing the same loop as an explicit graph. See
  [implementations/README.md](implementations/README.md) for a side-by-side
  comparison.
- **[failure_modes/](failure_modes/)** -- four ways generator-critic loops
  fail in practice, each with runnable code demonstrating the failure _and_
  the fix:
  - [`01_shallow_critique`](failure_modes/01_shallow_critique/) -- self-agreement, when the critic shares the generator's blind spots
  - [`02_unbounded_loops`](failure_modes/02_unbounded_loops/) -- hard iteration caps and token-budget tracking
  - [`03_diminishing_returns`](failure_modes/03_diminishing_returns/) -- instrumenting quality-per-iteration to see when gains flatten
  - [`04_skippable_critic`](failure_modes/04_skippable_critic/) -- enforcing call order structurally instead of hoping the LLM cooperates
- **[decision_guide/](decision_guide/)** -- when to use single-model
  self-critique vs. separate-model critique vs. tool-grounded critique
  (linter/compiler/schema validator), with cost/latency/quality tradeoffs.

## Running the examples

Requires Python >= 3.10 (the pinned `anthropic` SDK major version requires it).

```bash
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY
python implementations/raw_api/generator_critic.py
```

Every script under `implementations/` and `failure_modes/` is directly
runnable (`python path/to/script.py`) and makes real API calls -- each prints
its total token spend and estimated cost at the end. See
[implementations/README.md](implementations/README.md) for expected cost.

Target audience: developers who already know what an LLM API call looks
like. This isn't an intro to prompting.
