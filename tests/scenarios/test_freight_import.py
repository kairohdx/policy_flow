from dataclasses import dataclass
from decimal import Decimal

from policyflow import CollectAll, PolicyEngine, RuleResult, rule


@dataclass(frozen=True)
class FreightRequest:
    postal_code: int


@dataclass(frozen=True)
class FreightRange:
    key: str
    start: int
    end: int
    price: Decimal


def match_rule(freight_range: FreightRange):
    @rule(id=f"range-{freight_range.key}")
    def match(request: FreightRequest) -> RuleResult[FreightRange]:
        if not freight_range.start <= request.postal_code <= freight_range.end:
            return RuleResult.pass_(reason="outside_range")
        return RuleResult.consume(freight_range, reason="inside_range")

    return match


RANGES = [
    FreightRange("capital", 1000000, 1999999, Decimal("12.00")),
    FreightRange("promotion", 1500000, 1599999, Decimal("8.00")),
    FreightRange("interior", 2000000, 2999999, Decimal("18.00")),
]


def make_engine() -> PolicyEngine[FreightRequest, FreightRange]:
    engine = PolicyEngine[FreightRequest, FreightRange](name="freight")
    engine.add_scope(
        "freight.ranges",
        rules=[match_rule(item) for item in RANGES],
        strategy=CollectAll(),
    )
    return engine


def test_exactly_one_compatible_range_can_be_resolved() -> None:
    execution = make_engine().run(
        FreightRequest(2500000),
        scopes=["freight.ranges"],
    )

    assert len(execution.decisions) == 1
    assert execution.decision is not None
    assert execution.decision.effect == RANGES[2]


def test_no_compatible_range_is_observable() -> None:
    execution = make_engine().run(
        FreightRequest(9999999),
        scopes=["freight.ranges"],
    )

    assert execution.decisions == ()
    resolution = next(
        event
        for event in execution.trace.events
        if event.name == "resolution.no_match"
    )
    assert resolution.attributes["evaluated_rules"] == 3


def test_overlapping_ranges_are_exposed_instead_of_silently_resolved() -> None:
    execution = make_engine().run(
        FreightRequest(1550000),
        scopes=["freight.ranges"],
    )

    assert [decision.effect for decision in execution.decisions] == RANGES[:2]
    assert len(execution.decisions) == 2


def test_domain_can_classify_collect_all_cardinality() -> None:
    engine = make_engine()

    no_match = engine.run(
        FreightRequest(9999999),
        scopes=["freight.ranges"],
    )
    one_match = engine.run(
        FreightRequest(2500000),
        scopes=["freight.ranges"],
    )
    conflict = engine.run(
        FreightRequest(1550000),
        scopes=["freight.ranges"],
    )

    assert len(no_match.decisions) == 0
    assert len(one_match.decisions) == 1
    assert len(conflict.decisions) > 1

