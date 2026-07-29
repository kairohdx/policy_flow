import pytest

from policyflow import (
    DuplicateRuleError,
    DuplicateScopeError,
    FirstMatch,
    PolicyEngine,
    RuleResult,
    ScopeNotFoundError,
    rule,
)


@rule(id="same")
def first(_: object):
    return RuleResult.pass_()


@rule(id="same")
def second(_: object):
    return RuleResult.pass_()


def test_registry_rejects_duplicate_scope() -> None:
    engine = PolicyEngine[object, object]()
    engine.add_scope("scope", rules=[first], strategy=FirstMatch())

    with pytest.raises(DuplicateScopeError):
        engine.add_scope("scope", rules=[second], strategy=FirstMatch())


def test_registry_rejects_duplicate_rule_id_inside_scope() -> None:
    engine = PolicyEngine[object, object]()

    with pytest.raises(DuplicateRuleError):
        engine.add_scope("scope", rules=[first, second], strategy=FirstMatch())


def test_execution_rejects_unknown_scope() -> None:
    engine = PolicyEngine[object, object]()

    with pytest.raises(ScopeNotFoundError):
        engine.run(object(), scopes=["missing"])

