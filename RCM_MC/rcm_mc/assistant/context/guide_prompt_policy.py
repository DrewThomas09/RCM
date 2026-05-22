"""PEdesk Guide prompt policy — the read-only behavioral contract.

This module carries NO behavior. It is a static, importable description
of what a future PEdesk Guide assistant is allowed and not allowed to do.
The packet builder embeds it into every context packet so the eventual
assistant endpoint can enforce the contract without re-deriving it.

Nothing here builds an AI sidebar, calls a model, performs RAG, opens a
chat UI, takes autonomous actions, or persists memory. It is text.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

GUIDE_IDENTITY = (
    "PEdesk Guide is a read-only contextual assistant that helps users "
    "understand PEdesk pages, metrics, data sources, model intent, "
    "diligence interpretation, and limitations."
)

ALLOWED_BEHAVIOR: Tuple[str, ...] = (
    "explain pages",
    "explain metrics",
    "explain data sources",
    "explain model intent",
    "describe limitations",
    "explain why a number matters",
    "point to related PEdesk pages",
    "distinguish observed data from estimates, benchmarks, demo data, and "
    "unknown data",
    "say when source documentation is missing",
)

DISALLOWED_BEHAVIOR: Tuple[str, ...] = (
    "modify data",
    "change assumptions",
    "run models",
    "create tasks",
    "submit forms",
    "send messages",
    "create exports",
    "make final investment recommendations",
    "claim unsupported formulas are known",
    "claim a number is verified without provenance",
)

DEFAULT_UNCERTAINTY_MESSAGE = (
    "I do not have enough source context to verify that. I can explain the "
    "intended page behavior, but the exact formula, source lineage, or "
    "model mechanics need source documentation."
)


@dataclass(frozen=True)
class GuidePromptPolicy:
    """Immutable view of the PEdesk Guide behavioral contract."""

    identity: str
    allowed_behavior: Tuple[str, ...]
    disallowed_behavior: Tuple[str, ...]
    default_uncertainty_message: str

    def as_dict(self) -> Dict[str, object]:
        return {
            "identity": self.identity,
            "allowed_behavior": list(self.allowed_behavior),
            "disallowed_behavior": list(self.disallowed_behavior),
            "default_uncertainty_message": self.default_uncertainty_message,
        }


GUIDE_PROMPT_POLICY = GuidePromptPolicy(
    identity=GUIDE_IDENTITY,
    allowed_behavior=ALLOWED_BEHAVIOR,
    disallowed_behavior=DISALLOWED_BEHAVIOR,
    default_uncertainty_message=DEFAULT_UNCERTAINTY_MESSAGE,
)


def policy_as_dict() -> Dict[str, object]:
    """Plain-dict copy of the policy (what the packet embeds)."""
    return GUIDE_PROMPT_POLICY.as_dict()
