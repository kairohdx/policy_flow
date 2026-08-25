import asyncio

import pytest

from policyflow import (
    CollectAll,
    CollectResolvedScopes,
    FirstMatch,
    InvalidRuleResultError,
    PolicyEngine,
    RuleResult,
    ScopeNotFoundError,
    StopOnFirstResolvedScope,
    rule,
)


def evaluated_scopes(execution) -> list[str]:
    return [
        str(event.attributes["scope"])
        for event in execution.trace.events
        if event.name == "scope.entered"
    ]


def test_default_stops_on_first_resolved_scope() -> None:
    calls: list[str] = []

    @rule(id="first")
    def first(_: object) -> RuleResult[str]:
        calls.append("first")
        return RuleResult.consume("first")

    @rule(id="second")
    def second(_: object) -> RuleResult[str]:
        calls.append("second")
        return RuleResult.consume("second")

    engine = PolicyEngine[object, str]()
    engine.add_scope("scope-a", rules=[first], strategy=FirstMatch())
    engine.add_scope("scope-b", rules=[second], strategy=FirstMatch())

    execution = engine.run(object(), scopes=["scope-a", "scope-b"])

    assert [decision.effect for decision in execution.decisions] == ["first"]
    assert execution.decision == execution.decisions[0]
    assert calls == ["first"]
    assert evaluated_scopes(execution) == ["scope-a"]


def test_explicit_default_strategy_matches_implicit_default() -> None:
    @rule(id="first")
    def first(_: object) -> RuleResult[str]:
        return RuleResult.consume("first")

    @rule(id="second")
    def second(_: object) -> RuleResult[str]:
        return RuleResult.consume("second")

    engine = PolicyEngine[object, str]()
    engine.add_scope("scope-a", rules=[first], strategy=FirstMatch())
    engine.add_scope("scope-b", rules=[second], strategy=FirstMatch())

    execution = engine.run(
        object(),
        scopes=["scope-a", "scope-b"],
        traversal=StopOnFirstResolvedScope(),
    )

    assert [decision.rule_id for decision in execution.decisions] == ["first"]


def test_collects_decisions_from_multiple_scopes_in_requested_order() -> None:
    def matching_rule(rule_id: str, effect: str):
        @rule(id=rule_id)
        def match(_: object) -> RuleResult[str]:
            return RuleResult.consume(effect)

        return match

    engine = PolicyEngine[object, str]()
    engine.add_scope(
        "scope-c",
        rules=[matching_rule("c", "C")],
        strategy=FirstMatch(),
    )
    engine.add_scope(
        "scope-a",
        rules=[matching_rule("a", "A")],
        strategy=FirstMatch(),
    )
    engine.add_scope(
        "scope-b",
        rules=[matching_rule("b", "B")],
        strategy=FirstMatch(),
    )

    execution = engine.run(
        object(),
        scopes=["scope-b", "scope-c", "scope-a"],
        traversal=CollectResolvedScopes(),
    )

    assert [decision.effect for decision in execution.decisions] == ["B", "C", "A"]
    assert [decision.scope for decision in execution.decisions] == [
        "scope-b",
        "scope-c",
        "scope-a",
    ]
    assert execution.decision == execution.decisions[0]


def test_combines_first_match_and_collect_all_across_scopes() -> None:
    @rule(id="first-a")
    def first_a(_: object) -> RuleResult[str]:
        return RuleResult.consume("A1")

    @rule(id="ignored-a")
    def ignored_a(_: object) -> RuleResult[str]:
        return RuleResult.consume("A2")

    @rule(id="first-b")
    def first_b(_: object) -> RuleResult[str]:
        return RuleResult.consume("B1")

    @rule(id="pass-b")
    def pass_b(_: object) -> RuleResult[str]:
        return RuleResult.pass_()

    @rule(id="second-b")
    def second_b(_: object) -> RuleResult[str]:
        return RuleResult.block("B2")

    engine = PolicyEngine[object, str]()
    engine.add_scope(
        "first-match",
        rules=[first_a, ignored_a],
        strategy=FirstMatch(),
    )
    engine.add_scope(
        "collect-all",
        rules=[first_b, pass_b, second_b],
        strategy=CollectAll(),
    )

    execution = engine.run(
        object(),
        scopes=["first-match", "collect-all"],
        traversal=CollectResolvedScopes(),
    )

    assert [decision.effect for decision in execution.decisions] == [
        "A1",
        "B1",
        "B2",
    ]


def test_empty_and_unmatched_scopes_do_not_stop_or_add_decisions() -> None:
    @rule(id="pass")
    def pass_rule(_: object) -> RuleResult[str]:
        return RuleResult.pass_()

    @rule(id="match")
    def match(_: object) -> RuleResult[str]:
        return RuleResult.consume("matched")

    engine = PolicyEngine[object, str]()
    engine.add_scope("empty", rules=[], strategy=CollectAll())
    engine.add_scope("unmatched", rules=[pass_rule], strategy=FirstMatch())
    engine.add_scope("matched", rules=[match], strategy=FirstMatch())

    execution = engine.run(
        object(),
        scopes=["empty", "unmatched", "matched"],
        traversal=CollectResolvedScopes(),
    )

    assert [decision.effect for decision in execution.decisions] == ["matched"]
    assert evaluated_scopes(execution) == ["empty", "unmatched", "matched"]


def test_later_scope_failure_is_propagated_without_running_remaining_scopes() -> None:
    calls: list[str] = []

    @rule(id="resolved")
    def resolved(_: object) -> RuleResult[str]:
        calls.append("resolved")
        return RuleResult.consume("decision")

    @rule(id="broken")
    def broken(_: object):
        calls.append("broken")
        return "invalid"

    @rule(id="never")
    def never(_: object) -> RuleResult[str]:
        calls.append("never")
        return RuleResult.consume("never")

    engine = PolicyEngine[object, str]()
    engine.add_scope("resolved", rules=[resolved], strategy=FirstMatch())
    engine.add_scope("broken", rules=[broken], strategy=FirstMatch())
    engine.add_scope("remaining", rules=[never], strategy=FirstMatch())

    with pytest.raises(InvalidRuleResultError, match="broken"):
        engine.run(
            object(),
            scopes=["resolved", "broken", "remaining"],
            traversal=CollectResolvedScopes(),
        )

    assert calls == ["resolved", "broken"]


def test_scope_lookup_remains_lazy_for_default_and_eager_by_traversal() -> None:
    @rule(id="resolved")
    def resolved(_: object) -> RuleResult[str]:
        return RuleResult.consume("decision")

    engine = PolicyEngine[object, str]()
    engine.add_scope("resolved", rules=[resolved], strategy=FirstMatch())

    default_execution = engine.run(
        object(),
        scopes=["resolved", "missing"],
    )
    assert default_execution.decision is not None

    with pytest.raises(ScopeNotFoundError, match="missing"):
        engine.run(
            object(),
            scopes=["resolved", "missing"],
            traversal=CollectResolvedScopes(),
        )


def test_trace_describes_traversal_scopes_and_accumulated_decisions() -> None:
    @rule(id="pass")
    def pass_rule(_: object) -> RuleResult[str]:
        return RuleResult.pass_()

    @rule(id="first")
    def first(_: object) -> RuleResult[str]:
        return RuleResult.consume("first")

    @rule(id="second")
    def second(_: object) -> RuleResult[str]:
        return RuleResult.consume("second")

    engine = PolicyEngine[object, str]()
    engine.add_scope("empty", rules=[pass_rule], strategy=FirstMatch())
    engine.add_scope("scope-a", rules=[first], strategy=FirstMatch())
    engine.add_scope("scope-b", rules=[second], strategy=FirstMatch())

    execution = engine.run(
        object(),
        scopes=["empty", "scope-a", "scope-b"],
        traversal=CollectResolvedScopes(),
    )

    started = execution.trace.events[0]
    completed = execution.trace.events[-1]
    scope_exits = [
        event
        for event in execution.trace.events
        if event.name == "scope.exited"
    ]

    assert started.attributes["traversal_strategy"] == "collect_resolved_scopes"
    assert completed.attributes["traversal_strategy"] == "collect_resolved_scopes"
    assert completed.attributes["evaluated_scopes"] == [
        "empty",
        "scope-a",
        "scope-b",
    ]
    assert completed.attributes["resolved_scopes"] == ["scope-a", "scope-b"]
    assert completed.attributes["decision_count"] == 2
    assert completed.attributes["selected_rules"] == ["first", "second"]
    assert [event.attributes["decision_count"] for event in scope_exits] == [
        0,
        1,
        1,
    ]


async def test_arun_collects_sync_and_async_rules_across_scopes() -> None:
    @rule(id="sync")
    def sync_rule(_: object) -> RuleResult[str]:
        return RuleResult.consume("sync")

    @rule(id="async")
    async def async_rule(_: object) -> RuleResult[str]:
        await asyncio.sleep(0)
        return RuleResult.consume("async")

    engine = PolicyEngine[object, str]()
    engine.add_scope("sync", rules=[sync_rule], strategy=FirstMatch())
    engine.add_scope("async", rules=[async_rule], strategy=FirstMatch())

    execution = await engine.arun(
        object(),
        scopes=["sync", "async"],
        traversal=CollectResolvedScopes(),
    )

    assert [decision.effect for decision in execution.decisions] == [
        "sync",
        "async",
    ]
    assert execution.decision == execution.decisions[0]


async def test_arun_uses_same_stop_on_first_scope_default() -> None:
    calls: list[str] = []

    @rule(id="first")
    async def first(_: object) -> RuleResult[str]:
        await asyncio.sleep(0)
        calls.append("first")
        return RuleResult.consume("first")

    @rule(id="second")
    async def second(_: object) -> RuleResult[str]:
        await asyncio.sleep(0)
        calls.append("second")
        return RuleResult.consume("second")

    engine = PolicyEngine[object, str]()
    engine.add_scope("scope-a", rules=[first], strategy=FirstMatch())
    engine.add_scope("scope-b", rules=[second], strategy=FirstMatch())

    execution = await engine.arun(
        object(),
        scopes=["scope-a", "scope-b"],
    )

    assert [decision.effect for decision in execution.decisions] == ["first"]
    assert calls == ["first"]


def test_effect_values_are_not_executed() -> None:
    executed = False

    def effect() -> None:
        nonlocal executed
        executed = True

    @rule(id="callable-effect")
    def callable_effect(_: object) -> RuleResult[object]:
        return RuleResult.consume(effect)

    engine = PolicyEngine[object, object]()
    engine.add_scope(
        "scope",
        rules=[callable_effect],
        strategy=FirstMatch(),
    )

    execution = engine.run(
        object(),
        scopes=["scope"],
        traversal=CollectResolvedScopes(),
    )

    assert execution.decision is not None
    assert execution.decision.effect is effect
    assert executed is False
