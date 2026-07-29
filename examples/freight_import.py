"""Detect missing and overlapping freight ranges with CollectAll."""

from dataclasses import dataclass
from decimal import Decimal

from policyflow import CollectAll, PolicyEngine, RuleResult, rule


@dataclass(frozen=True, slots=True)
class FreightRow:
    postal_code: int


@dataclass(frozen=True, slots=True)
class FreightRange:
    name: str
    start: int
    end: int
    price: Decimal

    def contains(self, postal_code: int) -> bool:
        return self.start <= postal_code <= self.end


def range_rule(freight_range: FreightRange):
    @rule(
        id=f"match-{freight_range.name}",
        tags={"range": freight_range.name},
    )
    def match_range(row: FreightRow) -> RuleResult[FreightRange]:
        if not freight_range.contains(row.postal_code):
            return RuleResult.pass_(reason="postal_code_outside_range")
        return RuleResult.consume(
            freight_range,
            reason="postal_code_inside_range",
        )

    return match_range


def build_engine(
    ranges: list[FreightRange],
) -> PolicyEngine[FreightRow, FreightRange]:
    engine = PolicyEngine[FreightRow, FreightRange](name="freight-range-import")
    engine.add_scope(
        "freight.range-matching",
        rules=[range_rule(item) for item in ranges],
        strategy=CollectAll(),
    )
    return engine


def describe_match(
    engine: PolicyEngine[FreightRow, FreightRange],
    postal_code: int,
) -> str:
    execution = engine.run(
        FreightRow(postal_code),
        scopes=["freight.range-matching"],
    )

    if not execution.decisions:
        return "range_not_found"
    if len(execution.decisions) > 1:
        names = ", ".join(
            decision.effect.name
            for decision in execution.decisions
            if decision.effect is not None
        )
        return f"conflicting_ranges: {names}"

    matched = execution.decisions[0].effect
    assert matched is not None
    return f"resolved: {matched.name} ({matched.price})"


if __name__ == "__main__":
    configured_ranges = [
        FreightRange("capital", 1000000, 1999999, Decimal("12.00")),
        FreightRange("promotion", 1500000, 1599999, Decimal("8.00")),
        FreightRange("interior", 2000000, 2999999, Decimal("18.00")),
    ]
    freight_engine = build_engine(configured_ranges)

    print(describe_match(freight_engine, 2500000))
    print(describe_match(freight_engine, 9999999))
    print(describe_match(freight_engine, 1550000))

