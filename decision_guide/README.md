# Decision guide: which critic should you use?

"Add a critic" isn't one decision. There are at least four meaningfully
different mechanisms here, each with its own failure mode, and picking the
wrong one gets you the appearance of quality control without much of the
substance (see [failure_modes/01_shallow_critique](../failure_modes/01_shallow_critique)).

The cost and latency figures below are rough, not benchmarked. They'll shift
depending on your models, prompt sizes, and tooling, so treat this as a
starting point for your own measurements rather than something to cite.

| Approach                                                                                                     | Catches                                                                                                                     | Misses                                                                                                                               | Relative cost                         | Relative latency                                                        | Determinism                                                       | Use when                                                                                                                                                                    |
| ------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Single-model self-critique** (same model, fresh independent call)                                          | Surface-level spec compliance, obvious omissions                                                                            | Blind spots shared with the generator (the failure mode this repo opens with)                                                        | $ (1 extra call)                      | + ~1 round trip                                                         | Low; stochastic, no guarantee run to run                          | Low-stakes drafts, high-volume or cost-sensitive paths, a cheap sanity pass before shipping                                                                                 |
| **Same-model, adversarial/rubric prompt**                                                                    | More than a shallow self-critique gets you; an explicit checklist surfaces things a generic "does this work?" prompt misses | Still the same model's blind spots on things it fundamentally doesn't associate with risk                                            | $ (1 extra call, same model)          | + ~1 round trip                                                         | Low-medium                                                        | You want cheap uplift over shallow self-critique without adding a second model or vendor to your stack                                                                      |
| **Separate-model critique** (different model/tier/vendor as critic)                                          | Blind spots decorrelated from the generator: different training, different RLHF, different failure modes                    | Still probabilistic; won't catch what neither model was trained to flag                                                              | $$ (2 models, possibly a pricier one) | + ~1 round trip (sequential; critic needs the generator's output first) | Low-medium; better odds than same-model, but still not guaranteed | Medium-to-high-stakes generative tasks (code review, content with reputational risk) where a second, independent perspective actually matters and budget allows it          |
| **Tool-grounded critique** (linter, compiler, type-checker, test suite, schema validator, execute-and-check) | Exactly what the tool checks, reliably and reproducibly                                                                     | Anything outside the tool's rules: holistic design quality, security _reasoning_, semantic correctness the tool wasn't told to check | ¢ (local compute, no LLM tokens)      | Fast; typically sub-second, no model round trip                         | **Deterministic**: same input, same output, every time            | Any output with a formal, mechanically checkable spec: code (compiler/linter/types/tests), structured data (JSON Schema), SQL (dry-run/EXPLAIN), math (execute and compare) |

## Flowchart

```mermaid
flowchart TD
    A{"Deterministic checker available?<br/>(compiler / linter / type-checker /<br/>test suite / schema validator)"} -->|Yes| B["Tool-grounded critique<br/>as the hard gate"]
    A -->|No| C{"Cost of a bad output is high?<br/>(security-sensitive, customer-facing,<br/>hard to reverse)"}

    B --> B2["Layer an LLM critique on top only for what<br/>the tool can't check: design quality,<br/>security reasoning, judgment calls"]

    C -->|Yes| D["Separate-model critique<br/>(different vendor/tier than the generator)"]
    C -->|No| E{"High-volume or latency-sensitive?"}

    E -->|Yes| F["Single-model self-critique,<br/>or skip the critic entirely"]
    E -->|No| G["Same-model critique with an<br/>adversarial/rubric system prompt"]
```

## The recommended default for code generation

If your generator produces code, or anything else with a mechanical spec,
run the tool-grounded check first and make it a hard gate: the output has
to pass before an LLM critic ever sees it. A linter or test suite is
cheaper, faster, and more reliable than any LLM at catching what it's built
to catch. Save the slower, costlier LLM critique for what a tool can't
check: whether the design makes sense, whether there's a security
implication the type system won't see, whether this actually solves the
user's problem. Adding an LLM critique on top of a tool-grounded gate,
instead of picking one or the other, is usually the right call whenever a
deterministic checker exists at all.

The fixes in this repo aren't mutually exclusive either. Stacking a
tool-grounded gate, a separate-model critique, an iteration cap, and
structural enforcement of call order isn't overkill for a high-stakes
pipeline. It doesn't make much sense for a low-stakes one, though, so pick
based on what's actually at risk rather than out of habit.
