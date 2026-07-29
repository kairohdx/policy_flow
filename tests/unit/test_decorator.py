import inspect

from policyflow import RuleResult, rule


def test_decorator_preserves_original_function_signature() -> None:
    @rule(id="minimum-age", priority=10, tags={"domain": "signup"})
    def minimum_age(age: int) -> RuleResult[str]:
        return RuleResult.consume("allowed") if age >= 18 else RuleResult.block()

    assert minimum_age.__name__ == "minimum_age"
    assert list(inspect.signature(minimum_age).parameters) == ["age"]
    assert minimum_age(18).effect == "allowed"

