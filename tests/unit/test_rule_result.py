from types import MappingProxyType

import pytest

from policyflow import RuleOutcome, RuleResult


def test_result_factories_expose_explicit_control_flow() -> None:
    consumed = RuleResult.consume("effect", reason="matched", attributes={"score": 1})
    reask = RuleResult.reask(reason="invalid")
    passed = RuleResult.pass_(reason="not_owned")
    blocked = RuleResult.block(reason="forbidden")

    assert consumed.outcome is RuleOutcome.CONSUME
    assert consumed.effect == "effect"
    assert consumed.matched is True
    assert reask.outcome is RuleOutcome.REASK
    assert passed.outcome is RuleOutcome.PASS
    assert passed.matched is False
    assert blocked.outcome is RuleOutcome.BLOCK
    assert isinstance(consumed.attributes, MappingProxyType)


def test_result_rejects_empty_reason() -> None:
    with pytest.raises(ValueError, match="reason cannot be empty"):
        RuleResult.pass_(reason=" ")

