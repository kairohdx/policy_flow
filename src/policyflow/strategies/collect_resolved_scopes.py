"""Collect decisions from every requested scope."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from policyflow.core.execution import Decision

EffectT = TypeVar("EffectT")


@dataclass(frozen=True, slots=True)
class CollectResolvedScopes(Generic[EffectT]):
    """Continue through every requested scope and collect its decisions."""

    name: str = "collect_resolved_scopes"

    def should_stop(
        self,
        decisions: tuple[Decision[EffectT], ...],
    ) -> bool:
        return False
