"""Shared structured-output schema for critic responses.

Every example in this repo asks the critic for a typed Critique object
(via output_config / messages.parse) instead of free-text feedback. That
matters for the "skippable critic" failure mode in particular: you can't
structurally gate on a verdict you have to regex out of prose.
"""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


class Critique(BaseModel):
    score: int = Field(ge=0, le=100, description="Overall quality score, 0-100.")
    issues: List[str] = Field(
        default_factory=list,
        description="Concrete, specific problems found. Empty if none.",
    )
    verdict: Literal["pass", "revise"]
    reasoning: str = Field(description="One or two sentences explaining the verdict.")
