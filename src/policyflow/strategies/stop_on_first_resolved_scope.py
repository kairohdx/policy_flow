"""Stop traversal after the first scope that produces decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from policyflow.core.execution import Decision

EffectT = TypeVar("EffectT")


@dataclass(frozen=True, slots=True)
class StopOnFirstResolvedScope(Generic[EffectT]):
    """Stop after the first scope whose resolution selects decisions."""

    name: str = "stop_on_first_resolved_scope"

    def should_stop(
        self,
        decisions: tuple[Decision[EffectT], ...],
    ) -> bool:
        return bool(decisions)
