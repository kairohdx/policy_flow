"""Structural contracts for rule objects."""

from __future__ import annotations

from typing import Awaitable, Protocol, TypeVar

from policyflow.core.results import RuleResult

ContextT = TypeVar("ContextT", contravariant=True)
EffectT = TypeVar("EffectT", covariant=True)


class Rule(Protocol[ContextT, EffectT]):
    """An object rule accepted by PolicyEngine."""

    rule_id: str
    priority: int

    def evaluate(
        self,
        context: ContextT,
    ) -> RuleResult[EffectT] | Awaitable[RuleResult[EffectT]]:
        ...

