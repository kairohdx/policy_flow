"""Decorator used to declare function rules without wrapping their signature."""

from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec, TypeVar

from policyflow.typing import JsonValue

from .definition import RuleMetadata

P = ParamSpec("P")
ReturnT = TypeVar("ReturnT")

RULE_METADATA_ATTRIBUTE = "__policyflow_rule__"


def rule(
    *,
    id: str,
    priority: int = 100,
    tags: dict[str, JsonValue] | None = None,
) -> Callable[[Callable[P, ReturnT]], Callable[P, ReturnT]]:
    """Attach PolicyFlow metadata while preserving the original callable."""
    metadata = RuleMetadata(id, priority, tags or {})

    def decorate(function: Callable[P, ReturnT]) -> Callable[P, ReturnT]:
        setattr(function, RULE_METADATA_ATTRIBUTE, metadata)
        return function

    return decorate

