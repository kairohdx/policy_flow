from policyflow import FirstMatch, RuleResult


def test_first_match_selects_first_terminal_result() -> None:
    strategy = FirstMatch[str]()
    results = [
        RuleResult.pass_(reason="miss"),
        RuleResult.consume("winner"),
        RuleResult.consume("ignored"),
    ]

    assert strategy.should_stop(results[0]) is False
    assert strategy.should_stop(results[1]) is True
    assert strategy.select(results).effect == "winner"


def test_first_match_returns_none_when_all_rules_pass() -> None:
    strategy = FirstMatch[str]()

    assert strategy.select([RuleResult.pass_(), RuleResult.pass_()]) is None

