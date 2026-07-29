"""Completed engine execution values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Hashable, TypeVar

from policyflow.core.results import RuleResult
from policyflow.observability.trace import ExecutionTrace

EffectT = TypeVar("EffectT")


@dataclass(frozen=True, slots=True)
class Decision(Generic[EffectT]):
    rule_id: str
    scope: Hashable
    result: RuleResult[EffectT]

    @property
    def effect(self) -> EffectT | None:
        return self.result.effect

    @property
    def outcome(self):
        return self.result.outcome

    @property
    def reason(self) -> str | None:
        return self.result.reason


@dataclass(frozen=True, slots=True)
class Execution(Generic[EffectT]):
    decision: Decision[EffectT] | None
    trace: ExecutionTrace
