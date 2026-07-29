"""Normalized internal rule definitions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Generic, Mapping, TypeVar

from policyflow.core.results import RuleResult
from policyflow.typing import JsonValue

ContextT = TypeVar("ContextT")
EffectT = TypeVar("EffectT")

RuleCallable = Callable[
    [ContextT],
    RuleResult[EffectT] | Awaitable[RuleResult[EffectT]],
]


@dataclass(frozen=True, slots=True)
class RuleMetadata:
    """Static metadata attached by @rule."""

    rule_id: str
    priority: int = 100
    tags: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("rule id cannot be empty")
        object.__setattr__(self, "tags", MappingProxyType(dict(self.tags)))


@dataclass(frozen=True, slots=True)
class RuleDefinition(Generic[ContextT, EffectT]):
    """A function or object rule normalized for execution."""

    rule_id: str
    evaluate: RuleCallable[ContextT, EffectT]
    priority: int = 100
    tags: Mapping[str, JsonValue] = field(default_factory=dict)
    registration_order: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "tags", MappingProxyType(dict(self.tags)))

