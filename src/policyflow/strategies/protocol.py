"""Resolution strategy contracts."""

from __future__ import annotations

from typing import Protocol, TypeVar

from policyflow.core.results import RuleResult

EffectT = TypeVar("EffectT")


class ResolutionStrategy(Protocol[EffectT]):
    """Controls incremental rule evaluation and final selection."""

    name: str

    def should_stop(self, result: RuleResult[EffectT]) -> bool:
        ...

    def selected_indices(
        self,
        results: list[RuleResult[EffectT]],
    ) -> tuple[int, ...]:
        ...
