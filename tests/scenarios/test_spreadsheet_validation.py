from dataclasses import dataclass

from policyflow import CollectAll, PolicyEngine, RuleResult, rule


@dataclass(frozen=True)
class ProductRow:
    sku: str
    price: float
    stock: int


@dataclass(frozen=True)
class Issue:
    field: str
    code: str


@rule(id="sku-required", priority=10)
def sku_required(row: ProductRow) -> RuleResult[Issue]:
    if row.sku:
        return RuleResult.pass_(reason="sku_present")
    return RuleResult.block(Issue("sku", "required"), reason="sku_missing")


@rule(id="price-positive", priority=20)
def price_positive(row: ProductRow) -> RuleResult[Issue]:
    if row.price > 0:
        return RuleResult.pass_(reason="price_valid")
    return RuleResult.block(Issue("price", "not_positive"), reason="price_invalid")


@rule(id="stock-not-negative", priority=30)
def stock_not_negative(row: ProductRow) -> RuleResult[Issue]:
    if row.stock >= 0:
        return RuleResult.pass_(reason="stock_valid")
    return RuleResult.block(Issue("stock", "negative"), reason="stock_invalid")


def make_engine(
    *,
    stop_on_block: bool = False,
) -> PolicyEngine[ProductRow, Issue]:
    engine = PolicyEngine[ProductRow, Issue](name="product-import")
    engine.add_scope(
        "product.validation",
        rules=[sku_required, price_positive, stock_not_negative],
        strategy=CollectAll(stop_on_block=stop_on_block),
    )
    return engine


def test_collect_all_reports_every_problem_in_one_execution() -> None:
    execution = make_engine().run(
        ProductRow(sku="", price=-10, stock=-2),
        scopes=["product.validation"],
    )

    assert [decision.rule_id for decision in execution.decisions] == [
        "sku-required",
        "price-positive",
        "stock-not-negative",
    ]
    assert [decision.effect for decision in execution.decisions] == [
        Issue("sku", "required"),
        Issue("price", "not_positive"),
        Issue("stock", "negative"),
    ]
    # Compatibility for callers written against FirstMatch.
    assert execution.decision == execution.decisions[0]


def test_collect_all_returns_no_decisions_for_valid_row() -> None:
    execution = make_engine().run(
        ProductRow(sku="ABC", price=10, stock=2),
        scopes=["product.validation"],
    )

    assert execution.decisions == ()
    assert execution.decision is None


def test_collect_all_can_stop_at_first_block() -> None:
    execution = make_engine(stop_on_block=True).run(
        ProductRow(sku="", price=-10, stock=-2),
        scopes=["product.validation"],
    )

    assert [decision.rule_id for decision in execution.decisions] == [
        "sku-required"
    ]
    evaluated = [
        event.attributes["rule_id"]
        for event in execution.trace.events
        if event.name == "rule.evaluated"
    ]
    assert evaluated == ["sku-required"]


def test_trace_records_all_selected_rules_and_effects() -> None:
    execution = make_engine().run(
        ProductRow(sku="", price=-10, stock=5),
        scopes=["product.validation"],
    )

    resolution = next(
        event
        for event in execution.trace.events
        if event.name == "resolution.completed"
    )
    proposed = [
        event
        for event in execution.trace.events
        if event.name == "effect.proposed"
    ]

    assert resolution.attributes["decision_count"] == 2
    assert resolution.attributes["selected_rules"] == [
        "sku-required",
        "price-positive",
    ]
    assert [event.attributes["rule_id"] for event in proposed] == [
        "sku-required",
        "price-positive",
    ]
