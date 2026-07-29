"""Typed results produced by rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Generic, Mapping, TypeVar

from policyflow.typing import JsonValue

from .outcomes import RuleOutcome

EffectT = TypeVar("EffectT")


def _freeze_attributes(
    attributes: Mapping[str, JsonValue] | None,
) -> Mapping[str, JsonValue]:
    return MappingProxyType(dict(attributes or {}))


@dataclass(frozen=True, slots=True)
class RuleResult(Generic[EffectT]):
    """A domain decision plus its control-flow and observability metadata."""

    outcome: RuleOutcome
    effect: EffectT | None = None
    reason: str | None = None
    attributes: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.reason is not None and not self.reason.strip():
            raise ValueError("reason cannot be empty")
        object.__setattr__(self, "attributes", _freeze_attributes(self.attributes))

    @property
    def matched(self) -> bool:
        return self.outcome is not RuleOutcome.PASS

    @classmethod
    def consume(
        cls,
        effect: EffectT | None = None,
        *,
        reason: str | None = None,
        attributes: Mapping[str, JsonValue] | None = None,
    ) -> RuleResult[EffectT]:
        return cls(
            RuleOutcome.CONSUME,
            effect,
            reason,
            _freeze_attributes(attributes),
        )

    @classmethod
    def reask(
        cls,
        effect: EffectT | None = None,
        *,
        reason: str | None = None,
        attributes: Mapping[str, JsonValue] | None = None,
    ) -> RuleResult[EffectT]:
        return cls(
            RuleOutcome.REASK,
            effect,
            reason,
            _freeze_attributes(attributes),
        )

    @classmethod
    def pass_(
        cls,
        *,
        reason: str | None = None,
        attributes: Mapping[str, JsonValue] | None = None,
    ) -> RuleResult[EffectT]:
        return cls(
            RuleOutcome.PASS,
            None,
            reason,
            _freeze_attributes(attributes),
        )

    @classmethod
    def block(
        cls,
        effect: EffectT | None = None,
        *,
        reason: str | None = None,
        attributes: Mapping[str, JsonValue] | None = None,
    ) -> RuleResult[EffectT]:
        return cls(
            RuleOutcome.BLOCK,
            effect,
            reason,
            _freeze_attributes(attributes),
        )

