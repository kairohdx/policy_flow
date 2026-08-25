"""Scope traversal strategy contracts."""

from __future__ import annotations

from typing import Protocol, TypeVar

from policyflow.core.execution import Decision

EffectT = TypeVar("EffectT")


class ScopeTraversalStrategy(Protocol[EffectT]):
    """Controls whether execution continues after resolving one scope."""

    name: str

    def should_stop(
        self,
        decisions: tuple[Decision[EffectT], ...],
    ) -> bool:
        ...
