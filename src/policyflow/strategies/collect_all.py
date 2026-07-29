"""Collect every non-PASS rule result."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from policyflow.core.outcomes import RuleOutcome
from policyflow.core.results import RuleResult

EffectT = TypeVar("EffectT")


@dataclass(frozen=True, slots=True)
class CollectAll(Generic[EffectT]):
    """Evaluate all rules and select every result that is not PASS.

    ``stop_on_block`` is useful when BLOCK means that later evaluations would
    be unsafe or meaningless. It defaults to false so validation scenarios can
    report every applicable issue in one execution.
    """

    stop_on_block: bool = False
    name: str = "collect_all"

    def should_stop(self, result: RuleResult[EffectT]) -> bool:
        return self.stop_on_block and result.outcome is RuleOutcome.BLOCK

    def selected_indices(
        self,
        results: list[RuleResult[EffectT]],
    ) -> tuple[int, ...]:
        return tuple(
            index
            for index, result in enumerate(results)
            if result.outcome is not RuleOutcome.PASS
        )
