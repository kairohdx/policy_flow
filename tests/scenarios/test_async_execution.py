import asyncio

import pytest

from policyflow import (
    AsyncRuleInSyncExecutionError,
    FirstMatch,
    PolicyEngine,
    RuleResult,
    rule,
)


@rule(id="async-rule")
async def async_rule(value: str) -> RuleResult[str]:
    await asyncio.sleep(0)
    return RuleResult.consume(value.upper(), reason="async_completed")


def make_engine() -> PolicyEngine[str, str]:
    engine = PolicyEngine[str, str](name="async-example")
    engine.add_scope("default", rules=[async_rule], strategy=FirstMatch())
    return engine


async def test_arun_accepts_async_rules() -> None:
    execution = await make_engine().arun("hello", scopes=["default"])

    assert execution.decision is not None
    assert execution.decision.effect == "HELLO"


def test_run_explains_when_async_rule_requires_arun() -> None:
    with pytest.raises(AsyncRuleInSyncExecutionError, match=r"use arun\(\)"):
        make_engine().run("hello", scopes=["default"])

