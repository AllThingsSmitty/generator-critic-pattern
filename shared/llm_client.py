"""Thin wrapper around the Anthropic SDK shared by every example in this repo.

Kept deliberately small: every script in this repo calls the same three
functions (complete_text, complete_structured, extract_code_block) so the
*orchestration* differences between examples -- not client boilerplate --
are what stand out in the diffs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Type, TypeVar

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()  # picks up ANTHROPIC_API_KEY from a .env file if present

T = TypeVar("T", bound=BaseModel)

# Generator produces the artifact; same-model critic reuses it to demonstrate
# shared blind spots (see failure_modes/01_shallow_critique). Swap these for
# cheaper models (e.g. claude-haiku-4-5) if you're iterating on the examples
# and want faster/cheaper loops -- quality of the critique will drop with it,
# which is itself part of the lesson in the decision guide.
DEFAULT_GENERATOR_MODEL = "claude-opus-5"
DEFAULT_CRITIC_MODEL = "claude-opus-5"
DEFAULT_INDEPENDENT_CRITIC_MODEL = "claude-sonnet-5"

# $ per 1M tokens (input, output). Used only for the cost math in the
# token-budget and diminishing-returns examples -- update if pricing changes.
MODEL_PRICING = {
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


@dataclass
class Usage:
    input_tokens: int
    output_tokens: int
    model: str

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def cost_usd(self) -> float:
        in_price, out_price = MODEL_PRICING.get(self.model, (0.0, 0.0))
        return (self.input_tokens / 1_000_000) * in_price + (
            self.output_tokens / 1_000_000
        ) * out_price


@dataclass
class TokenBudget:
    """Hard cap on cumulative tokens spent across a generator-critic loop.

    This is the fix for the "unbounded loop" failure mode: a max_iterations
    cap alone doesn't protect you if individual iterations balloon in size
    (e.g. the generator starts dumping long explanations). Track actual
    spend and stop on whichever limit is hit first.
    """

    max_total_tokens: int
    spent_tokens: int = 0
    usage_log: list[Usage] = field(default_factory=list)

    def record(self, usage: Usage) -> None:
        self.spent_tokens += usage.total_tokens
        self.usage_log.append(usage)

    def exceeded(self) -> bool:
        return self.spent_tokens >= self.max_total_tokens

    def remaining(self) -> int:
        return max(0, self.max_total_tokens - self.spent_tokens)

    @property
    def total_cost_usd(self) -> float:
        return sum(u.cost_usd for u in self.usage_log)


_client: Optional[anthropic.Anthropic] = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        # Resolves ANTHROPIC_API_KEY (or an `ant auth login` profile)
        # from the environment -- see .env.example.
        _client = anthropic.Anthropic()
    return _client


def complete_text(
    model: str, system: str, user: str, max_tokens: int = 4096
) -> tuple[str, Usage]:
    """One-shot text completion. Returns (text, usage)."""
    client = get_client()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    usage = Usage(response.usage.input_tokens, response.usage.output_tokens, model)
    return text, usage


def complete_structured(
    model: str, system: str, user: str, output_model: Type[T], max_tokens: int = 4096
) -> tuple[T, Usage]:
    """Completion validated against a Pydantic model. Returns (parsed, usage).

    Used for critiques specifically so verdicts are a typed, machine-checkable
    field (Critique.verdict) rather than something we regex out of prose.
    """
    client = get_client()
    response = client.messages.parse(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=output_model,
    )
    usage = Usage(response.usage.input_tokens, response.usage.output_tokens, model)
    return response.parsed_output, usage


_CODE_BLOCK_RE = re.compile(r"```(?:\w+)?\s*\n(.*?)```", re.DOTALL)


def extract_code_block(text: str) -> str:
    """Pull the first fenced code block out of a model response.

    Falls back to the raw text if the model didn't fence its answer --
    generator system prompts in this repo ask for a fenced block, but real
    models occasionally skip it, and silently returning an empty string
    would be a worse failure than returning the unfenced text.
    """
    match = _CODE_BLOCK_RE.search(text)
    return match.group(1).strip() if match else text.strip()
