"""PolicyEngine orchestration."""

from __future__ import annotations

import inspect
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Generic, Hashable, TypeVar, cast

from policyflow.core.exceptions import (
    AsyncRuleInSyncExecutionError,
    InvalidRuleResultError,
)
from policyflow.core.execution import Decision, Execution
from policyflow.core.results import RuleResult
from policyflow.observability.collector import TraceCollector
from policyflow.observability.context import TraceContext
from policyflow.scopes.registry import ScopeRegistry
from policyflow.strategies.protocol import ResolutionStrategy
from policyflow.strategies.scope_traversal import ScopeTraversalStrategy
from policyflow.strategies.stop_on_first_resolved_scope import (
    StopOnFirstResolvedScope,
)
from policyflow.typing import JsonValue

ContextT = TypeVar("ContextT")
EffectT = TypeVar("EffectT")


@dataclass(frozen=True, slots=True)
class _TraversalResult(Generic[EffectT]):
    decisions: tuple[Decision[EffectT], ...]
    evaluated_scopes: tuple[Hashable, ...]
    resolved_scopes: tuple[Hashable, ...]


class PolicyEngine(Generic[ContextT, EffectT]):
    """Execute typed rules from explicitly selected scopes."""

    def __init__(self, *, name: str = "policyflow") -> None:
        if not name.strip():
            raise ValueError("engine name cannot be empty")
        self.name = name
        self._registry: ScopeRegistry[ContextT, EffectT] = ScopeRegistry()

    def add_scope(
        self,
        scope: Hashable,
        *,
        rules: Iterable[object],
        strategy: ResolutionStrategy[EffectT],
    ) -> None:
        self._registry.add(scope, rules=rules, strategy=strategy)

    def run(
        self,
        context: ContextT,
        *,
        scopes: Iterable[Hashable],
        traversal: ScopeTraversalStrategy[EffectT] | None = None,
        trace_context: TraceContext | None = None,
        trace_attributes: Mapping[str, JsonValue] | None = None,
    ) -> Execution[EffectT]:
        """Run synchronous rules. Use arun() when any rule is asynchronous."""
        if traversal is None:
            traversal = StopOnFirstResolvedScope()
        collector = self._start_trace(
            traversal,
            trace_context,
            trace_attributes,
        )
        try:
            result = self._run_sync(
                context,
                tuple(scopes),
                traversal,
                collector,
            )
        except Exception as exc:
            self._record_failure(collector, exc)
            raise
        return self._complete(collector, traversal, result)

    async def arun(
        self,
        context: ContextT,
        *,
        scopes: Iterable[Hashable],
        traversal: ScopeTraversalStrategy[EffectT] | None = None,
        trace_context: TraceContext | None = None,
        trace_attributes: Mapping[str, JsonValue] | None = None,
    ) -> Execution[EffectT]:
        """Run synchronous and asynchronous rules."""
        if traversal is None:
            traversal = StopOnFirstResolvedScope()
        collector = self._start_trace(
            traversal,
            trace_context,
            trace_attributes,
        )
        try:
            result = await self._run_async(
                context,
                tuple(scopes),
                traversal,
                collector,
            )
        except Exception as exc:
            self._record_failure(collector, exc)
            raise
        return self._complete(collector, traversal, result)

    def _start_trace(
        self,
        traversal: ScopeTraversalStrategy[EffectT],
        trace_context: TraceContext | None,
        trace_attributes: Mapping[str, JsonValue] | None,
    ) -> TraceCollector:
        collector = TraceCollector(
            pipeline=self.name,
            context=trace_context,
            attributes=trace_attributes,
        )
        collector.emit(
            "execution.started",
            attributes={
                "pipeline": self.name,
                "traversal_strategy": traversal.name,
                **self._trace_context_attributes(trace_context),
            },
        )
        return collector

    @staticmethod
    def _trace_context_attributes(
        context: TraceContext | None,
    ) -> dict[str, JsonValue]:
        if context is None:
            return {}
        attributes: dict[str, JsonValue] = {}
        if context.correlation_id is not None:
            attributes["correlation_id"] = context.correlation_id
        if context.parent_execution_id is not None:
            attributes["parent_execution_id"] = context.parent_execution_id
        return attributes

    def _run_sync(
        self,
        context: ContextT,
        scopes: tuple[Hashable, ...],
        traversal: ScopeTraversalStrategy[EffectT],
        collector: TraceCollector,
    ) -> _TraversalResult[EffectT]:
        accumulated: list[Decision[EffectT]] = []
        evaluated_scopes: list[Hashable] = []
        resolved_scopes: list[Hashable] = []
        for scope in scopes:
            definition = self._registry.get(scope)
            evaluated_scopes.append(scope)
            collector.emit(
                "scope.entered",
                attributes={
                    "scope": str(scope),
                    "strategy": definition.strategy.name,
                },
            )
            results: list[tuple[str, RuleResult[EffectT]]] = []
            for registered_rule in definition.rules:
                started = collector.tick()
                raw_result = registered_rule.evaluate(context)
                if inspect.isawaitable(raw_result):
                    close = getattr(raw_result, "close", None)
                    if callable(close):
                        close()
                    raise AsyncRuleInSyncExecutionError(
                        f"rule {registered_rule.rule_id!r} is asynchronous; use arun()"
                    )
                result = self._validate_result(registered_rule.rule_id, raw_result)
                duration = collector.elapsed_ms(started, collector.tick())
                self._record_rule(
                    collector,
                    scope,
                    registered_rule.rule_id,
                    registered_rule.tags,
                    result,
                    duration,
                )
                results.append((registered_rule.rule_id, result))
                if definition.strategy.should_stop(result):
                    break

            decisions = self._resolve(
                scope,
                definition.strategy,
                results,
                collector,
            )
            self._record_scope_exit(collector, scope, decisions)
            if self._advance_traversal(
                traversal,
                scope,
                decisions,
                accumulated,
                resolved_scopes,
            ):
                break
        return _TraversalResult(
            decisions=tuple(accumulated),
            evaluated_scopes=tuple(evaluated_scopes),
            resolved_scopes=tuple(resolved_scopes),
        )

    async def _run_async(
        self,
        context: ContextT,
        scopes: tuple[Hashable, ...],
        traversal: ScopeTraversalStrategy[EffectT],
        collector: TraceCollector,
    ) -> _TraversalResult[EffectT]:
        accumulated: list[Decision[EffectT]] = []
        evaluated_scopes: list[Hashable] = []
        resolved_scopes: list[Hashable] = []
        for scope in scopes:
            definition = self._registry.get(scope)
            evaluated_scopes.append(scope)
            collector.emit(
                "scope.entered",
                attributes={
                    "scope": str(scope),
                    "strategy": definition.strategy.name,
                },
            )
            results: list[tuple[str, RuleResult[EffectT]]] = []
            for registered_rule in definition.rules:
                started = collector.tick()
                raw_result = registered_rule.evaluate(context)
                if inspect.isawaitable(raw_result):
                    raw_result = await raw_result
                result = self._validate_result(registered_rule.rule_id, raw_result)
                duration = collector.elapsed_ms(started, collector.tick())
                self._record_rule(
                    collector,
                    scope,
                    registered_rule.rule_id,
                    registered_rule.tags,
                    result,
                    duration,
                )
                results.append((registered_rule.rule_id, result))
                if definition.strategy.should_stop(result):
                    break

            decisions = self._resolve(
                scope,
                definition.strategy,
                results,
                collector,
            )
            self._record_scope_exit(collector, scope, decisions)
            if self._advance_traversal(
                traversal,
                scope,
                decisions,
                accumulated,
                resolved_scopes,
            ):
                break
        return _TraversalResult(
            decisions=tuple(accumulated),
            evaluated_scopes=tuple(evaluated_scopes),
            resolved_scopes=tuple(resolved_scopes),
        )

    @staticmethod
    def _advance_traversal(
        traversal: ScopeTraversalStrategy[EffectT],
        scope: Hashable,
        decisions: tuple[Decision[EffectT], ...],
        accumulated: list[Decision[EffectT]],
        resolved_scopes: list[Hashable],
    ) -> bool:
        accumulated.extend(decisions)
        if decisions:
            resolved_scopes.append(scope)
        return traversal.should_stop(decisions)

    @staticmethod
    def _record_scope_exit(
        collector: TraceCollector,
        scope: Hashable,
        decisions: tuple[Decision[EffectT], ...],
    ) -> None:
        collector.emit(
            "scope.exited",
            attributes={
                "scope": str(scope),
                "decision_count": len(decisions),
                "selected_rules": [
                    decision.rule_id for decision in decisions
                ],
                "outcomes": [
                    decision.outcome.value for decision in decisions
                ],
            },
        )

    @staticmethod
    def _validate_result(rule_id: str, result: object) -> RuleResult[EffectT]:
        if not isinstance(result, RuleResult):
            raise InvalidRuleResultError(
                f"rule {rule_id!r} must return RuleResult, got {type(result).__name__}"
            )
        return cast(RuleResult[EffectT], result)

    @staticmethod
    def _record_rule(
        collector: TraceCollector,
        scope: Hashable,
        rule_id: str,
        tags: Mapping[str, JsonValue],
        result: RuleResult[EffectT],
        duration_ms: float,
    ) -> None:
        attributes: dict[str, JsonValue] = {
            "scope": str(scope),
            "rule_id": rule_id,
            "matched": result.matched,
            "outcome": result.outcome.value,
        }
        if result.reason is not None:
            attributes["reason"] = result.reason
        if tags:
            attributes["tags"] = dict(tags)
        attributes.update(result.attributes)
        collector.emit(
            "rule.evaluated",
            duration_ms=duration_ms,
            attributes=attributes,
        )

    @staticmethod
    def _resolve(
        scope: Hashable,
        strategy: ResolutionStrategy[EffectT],
        results: list[tuple[str, RuleResult[EffectT]]],
        collector: TraceCollector,
    ) -> tuple[Decision[EffectT], ...]:
        selected_indices = strategy.selected_indices(
            [result for _, result in results]
        )
        if not selected_indices:
            collector.emit(
                "resolution.no_match",
                attributes={
                    "scope": str(scope),
                    "strategy": strategy.name,
                    "evaluated_rules": len(results),
                },
            )
            return ()

        decisions = tuple(
            Decision(
                rule_id=results[index][0],
                scope=scope,
                result=results[index][1],
            )
            for index in selected_indices
        )
        collector.emit(
            "resolution.completed",
            attributes={
                "scope": str(scope),
                "strategy": strategy.name,
                "evaluated_rules": len(results),
                "decision_count": len(decisions),
                "selected_rules": [decision.rule_id for decision in decisions],
                "outcomes": [
                    decision.outcome.value
                    for decision in decisions
                ],
            },
        )
        for decision in decisions:
            if decision.effect is None:
                continue
            collector.emit(
                "effect.proposed",
                attributes={
                    "scope": str(scope),
                    "rule_id": decision.rule_id,
                    "effect_type": type(decision.effect).__name__,
                },
            )
        return decisions

    @staticmethod
    def _record_failure(collector: TraceCollector, exc: Exception) -> None:
        collector.emit(
            "execution.failed",
            attributes={
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        )
        collector.finish("failed")

    @staticmethod
    def _complete(
        collector: TraceCollector,
        traversal: ScopeTraversalStrategy[EffectT],
        result: _TraversalResult[EffectT],
    ) -> Execution[EffectT]:
        decisions = result.decisions
        attributes: dict[str, JsonValue] = {
            "matched": bool(decisions),
            "decision_count": len(decisions),
            "traversal_strategy": traversal.name,
            "evaluated_scopes": [
                str(scope) for scope in result.evaluated_scopes
            ],
            "resolved_scopes": [
                str(scope) for scope in result.resolved_scopes
            ],
        }
        if decisions:
            attributes.update(
                {
                    "scope": str(decisions[0].scope),
                    "selected_rules": [
                        decision.rule_id
                        for decision in decisions
                    ],
                    "outcomes": [
                        decision.outcome.value
                        for decision in decisions
                    ],
                }
            )
        collector.emit("execution.completed", attributes=attributes)
        return Execution(decisions=decisions, trace=collector.finish("completed"))
