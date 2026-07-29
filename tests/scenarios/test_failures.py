import pytest

from policyflow import FirstMatch, InvalidRuleResultError, PolicyEngine, rule


@rule(id="broken")
def broken_rule(_: object):
    return "not-a-rule-result"


def test_invalid_result_raises_public_error() -> None:
    engine = PolicyEngine[object, object]()
    engine.add_scope("default", rules=[broken_rule], strategy=FirstMatch())

    with pytest.raises(InvalidRuleResultError, match="broken"):
        engine.run(object(), scopes=["default"])

