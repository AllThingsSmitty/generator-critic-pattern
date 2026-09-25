# Reference implementations

Both scripts implement the same loop against the same task (`parse_log_line`,
defined at the top of each file), so you can diff them directly and see what
the framework actually adds.

|                                | [`raw_api/generator_critic.py`](raw_api/generator_critic.py) | [`langgraph/generator_critic_graph.py`](langgraph/generator_critic_graph.py)                                           |
| ------------------------------ | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| Control flow                   | Explicit `for` loop, `break` on stop condition               | `StateGraph` with a conditional edge (`route_after_critique`)                                                          |
| Stopping logic                 | Inline in the loop body                                      | Isolated in one routing function, callable and testable on its own                                                     |
| Dependencies                   | `anthropic`, `pydantic`                                      | + `langgraph`                                                                                                          |
| Unbounded-loop guard           | `MAX_ITERATIONS` + `TokenBudget`                             | Same, plus LangGraph's own `recursion_limit` as a second backstop                                                      |
| Inspectability                 | Read the loop                                                | `app.get_graph().draw_mermaid()` renders the graph structure                                                           |
| When this shape earns its keep | Small, linear pipelines                                      | Multiple critics, branching repair strategies, or you want the graph structure itself visualized as the pipeline grows |

Neither one is "the" correct implementation. The pattern is the loop, not
what you build it in (see the [top-level README](../README.md)). Reach for
LangGraph once the orchestration gets complicated enough that you'd rather
see it as a graph than as nested conditionals in a function: multiple
critic types routed conditionally, parallel critics, human-in-the-loop
interrupts. For one generator and one critic, the raw loop is fewer lines
and one less dependency to think about.

## Running

```bash
pip install -r ../requirements.txt
cp ../.env.example ../.env   # fill in ANTHROPIC_API_KEY
python raw_api/generator_critic.py
python langgraph/generator_critic_graph.py
```

Each run makes a handful of real API calls: generator and critic, once per
iteration, up to `MAX_ITERATIONS`. With the default models that's usually a
few dollars at most, and both scripts print total tokens and cost when
they're done.
