from policyflow import CollectAll, RuleResult


def test_collect_all_selects_every_non_pass_result() -> None:
    strategy = CollectAll[str]()
    results = [
        RuleResult.pass_(reason="not_applicable"),
        RuleResult.consume("warning"),
        RuleResult.reask("missing_value"),
        RuleResult.block("invalid_value"),
    ]

    assert strategy.selected_indices(results) == (1, 2, 3)
    assert all(not strategy.should_stop(result) for result in results)


def test_collect_all_can_stop_evaluation_on_block() -> None:
    strategy = CollectAll[str](stop_on_block=True)

    assert strategy.should_stop(RuleResult.consume("warning")) is False
    assert strategy.should_stop(RuleResult.block("fatal")) is True


def test_collect_all_returns_empty_selection_when_every_rule_passes() -> None:
    strategy = CollectAll[str]()

    assert strategy.selected_indices(
        [RuleResult.pass_(), RuleResult.pass_()]
    ) == ()

