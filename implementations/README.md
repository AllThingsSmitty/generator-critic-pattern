# Reference implementations

Both scripts implement the exact same loop against the exact same task
(`parse_log_line`, defined at the top of each file) so you can diff them
directly and see what a framework actually buys you.

| | [`raw_api/generator_critic.py`](raw_api/generator_critic.py) | [`langgraph/generator_critic_graph.py`](langgraph/generator_critic_graph.py) |
|---|---|---|
| Control flow | Explicit `for` loop, `break` on stop condition | `StateGraph` with a conditional edge (`route_after_critique`) |
| Stopping logic | Inline in the loop body | Isolated in one routing function, callable/testable on its own |
| Dependencies | `anthropic`, `pydantic` | + `langgraph` |
| Unbounded-loop guard | `MAX_ITERATIONS` + `TokenBudget` | Same, plus LangGraph's own `recursion_limit` as a second backstop |
| Inspectability | Read the loop | `app.get_graph().draw_mermaid()` renders the graph structure |
| When this shape earns its keep | Small, linear pipelines | Multiple critics, branching repair strategies, or you want the graph structure itself to be inspectable/visualizable as the pipeline grows |

Neither implementation is "the" correct one. The pattern is the loop, not the
tooling around it -- see the [top-level README](../README.md). Reach for
LangGraph when the orchestration itself gets complex enough (multiple critic
types routed conditionally, parallel critics, human-in-the-loop interrupts)
that you want that complexity represented as a graph instead of nested
conditionals in a function body. For a single generator and a single critic,
the raw loop is less code and has one fewer dependency to reason about.

## Running

```bash
pip install -r ../requirements.txt
cp ../.env.example ../.env   # fill in ANTHROPIC_API_KEY
python raw_api/generator_critic.py
python langgraph/generator_critic_graph.py
```

Each run makes a handful of real API calls (generator + critic, per
iteration, up to `MAX_ITERATIONS`). Expect low-single-digit-dollar cost at
most with the default models -- both scripts print total tokens and cost at
the end.
