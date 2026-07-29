"""PolicyEngine orchestration."""

from __future__ import annotations

import inspect
from collections.abc import Iterable, Mapping
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
from policyflow.typing import JsonValue

ContextT = TypeVar("ContextT")
EffectT = TypeVar("EffectT")
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
        trace_context: TraceContext | None = None,
        trace_attributes: Mapping[str, JsonValue] | None = None,
    ) -> Execution[EffectT]:
        """Run synchronous rules. Use arun() when any rule is asynchronous."""
        collector = self._start_trace(trace_context, trace_attributes)
        try:
            decision = self._run_sync(context, tuple(scopes), collector)
        except Exception as exc:
            self._record_failure(collector, exc)
            raise
        return self._complete(collector, decision)

    async def arun(
        self,
        context: ContextT,
        *,
        scopes: Iterable[Hashable],
        trace_context: TraceContext | None = None,
        trace_attributes: Mapping[str, JsonValue] | None = None,
    ) -> Execution[EffectT]:
        """Run synchronous and asynchronous rules."""
        collector = self._start_trace(trace_context, trace_attributes)
        try:
            decision = await self._run_async(context, tuple(scopes), collector)
        except Exception as exc:
            self._record_failure(collector, exc)
            raise
        return self._complete(collector, decision)

    def _start_trace(
        self,
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
        collector: TraceCollector,
    ) -> Decision[EffectT] | None:
        for scope in scopes:
            definition = self._registry.get(scope)
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

            decision = self._resolve(
                scope,
                definition.strategy,
                results,
                collector,
            )
            collector.emit(
                "scope.exited",
                attributes={
                    "scope": str(scope),
                    "decision": decision is not None,
                },
            )
            if decision is not None:
                return decision
        return None

    async def _run_async(
        self,
        context: ContextT,
        scopes: tuple[Hashable, ...],
        collector: TraceCollector,
    ) -> Decision[EffectT] | None:
        for scope in scopes:
            definition = self._registry.get(scope)
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

            decision = self._resolve(
                scope,
                definition.strategy,
                results,
                collector,
            )
            collector.emit(
                "scope.exited",
                attributes={
                    "scope": str(scope),
                    "decision": decision is not None,
                },
            )
            if decision is not None:
                return decision
        return None

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
    ) -> Decision[EffectT] | None:
        selected = strategy.select([result for _, result in results])
        if selected is None:
            collector.emit(
                "resolution.no_match",
                attributes={
                    "scope": str(scope),
                    "strategy": strategy.name,
                    "evaluated_rules": len(results),
                },
            )
            return None

        selected_rule_id = next(
            rule_id for rule_id, result in results if result is selected
        )
        collector.emit(
            "resolution.completed",
            attributes={
                "scope": str(scope),
                "strategy": strategy.name,
                "evaluated_rules": len(results),
                "selected_rule": selected_rule_id,
                "outcome": selected.outcome.value,
            },
        )
        if selected.effect is not None:
            collector.emit(
                "effect.proposed",
                attributes={
                    "scope": str(scope),
                    "rule_id": selected_rule_id,
                    "effect_type": type(selected.effect).__name__,
                },
            )
        return Decision(selected_rule_id, scope, selected)

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
        decision: Decision[EffectT] | None,
    ) -> Execution[EffectT]:
        attributes: dict[str, JsonValue] = {
            "matched": decision is not None,
        }
        if decision is not None:
            attributes.update(
                {
                    "scope": str(decision.scope),
                    "selected_rule": decision.rule_id,
                    "outcome": decision.outcome.value,
                }
            )
        collector.emit("execution.completed", attributes=attributes)
        return Execution(decision=decision, trace=collector.finish("completed"))
