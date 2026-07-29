"""First terminal rule wins."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from policyflow.core.results import RuleResult

EffectT = TypeVar("EffectT")


@dataclass(frozen=True, slots=True)
class FirstMatch(Generic[EffectT]):
    """Stop at the first result whose outcome is not PASS."""

    name: str = "first_match"

    def should_stop(self, result: RuleResult[EffectT]) -> bool:
        return result.outcome.terminal

    def selected_indices(
        self,
        results: list[RuleResult[EffectT]],
    ) -> tuple[int, ...]:
        for index, result in enumerate(results):
            if result.outcome.terminal:
                return (index,)
        return ()
