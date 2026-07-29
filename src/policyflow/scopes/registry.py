"""Scope registration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Hashable, Iterable, TypeVar

from policyflow.core.exceptions import (
    DuplicateRuleError,
    DuplicateScopeError,
    ScopeNotFoundError,
)
from policyflow.rules.definition import RuleDefinition
from policyflow.rules.registry import normalize_rule
from policyflow.strategies.protocol import ResolutionStrategy

ContextT = TypeVar("ContextT")
EffectT = TypeVar("EffectT")
@dataclass(frozen=True, slots=True)
class ScopeDefinition(Generic[ContextT, EffectT]):
    scope: Hashable
    rules: tuple[RuleDefinition[ContextT, EffectT], ...]
    strategy: ResolutionStrategy[EffectT]


class ScopeRegistry(Generic[ContextT, EffectT]):
    """Mutable configuration registry used before engine execution."""

    def __init__(self) -> None:
        self._scopes: dict[Hashable, ScopeDefinition[ContextT, EffectT]] = {}
        self._next_registration_order = 0

    def add(
        self,
        scope: Hashable,
        *,
        rules: Iterable[object],
        strategy: ResolutionStrategy[EffectT],
    ) -> ScopeDefinition[ContextT, EffectT]:
        if scope in self._scopes:
            raise DuplicateScopeError(f"scope {scope!r} is already registered")

        normalized: list[RuleDefinition[ContextT, EffectT]] = []
        ids: set[str] = set()
        for candidate in rules:
            definition = normalize_rule(
                candidate,
                registration_order=self._next_registration_order,
            )
            self._next_registration_order += 1
            if definition.rule_id in ids:
                raise DuplicateRuleError(
                    f"rule {definition.rule_id!r} is duplicated in scope {scope!r}"
                )
            ids.add(definition.rule_id)
            normalized.append(definition)

        normalized.sort(key=lambda item: (item.priority, item.registration_order))
        definition = ScopeDefinition(
            scope=scope,
            rules=tuple(normalized),
            strategy=strategy,
        )
        self._scopes[scope] = definition
        return definition

    def get(self, scope: Hashable) -> ScopeDefinition[ContextT, EffectT]:
        try:
            return self._scopes[scope]
        except KeyError as exc:
            raise ScopeNotFoundError(f"scope {scope!r} is not registered") from exc
