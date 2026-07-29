from dataclasses import dataclass

from policyflow import FirstMatch, PolicyEngine, RuleResult, rule


@dataclass(frozen=True)
class Context:
    message: str


@dataclass(frozen=True)
class ConfirmAddress:
    pass


@dataclass(frozen=True)
class ConfirmOrder:
    pass


@dataclass(frozen=True)
class CancelOrder:
    pass


Effect = ConfirmAddress | ConfirmOrder | CancelOrder


@rule(id="cancel-order")
def cancel_order(ctx: Context) -> RuleResult[Effect]:
    if ctx.message != "cancelar pedido":
        return RuleResult.pass_(reason="not_cancel")
    return RuleResult.consume(CancelOrder(), reason="cancelled")


@rule(id="confirm-address")
def confirm_address(ctx: Context) -> RuleResult[Effect]:
    if ctx.message != "sim":
        return RuleResult.reask(reason="address_confirmation_required")
    return RuleResult.consume(ConfirmAddress(), reason="address_confirmed")


@rule(id="confirm-order")
def confirm_order(ctx: Context) -> RuleResult[Effect]:
    if ctx.message != "sim":
        return RuleResult.reask(reason="order_confirmation_required")
    return RuleResult.consume(ConfirmOrder(), reason="order_confirmed")


def make_engine() -> PolicyEngine[Context, Effect]:
    engine = PolicyEngine[Context, Effect](name="chat-turn")
    engine.add_scope("global", rules=[cancel_order], strategy=FirstMatch())
    engine.add_scope(
        "delivery.address-preview",
        rules=[confirm_address],
        strategy=FirstMatch(),
    )
    engine.add_scope(
        "order.confirmation",
        rules=[confirm_order],
        strategy=FirstMatch(),
    )
    return engine


def evaluated_rules(execution) -> list[str]:
    return [
        str(event.attributes["rule_id"])
        for event in execution.trace.events
        if event.name == "rule.evaluated"
    ]


def test_yes_belongs_to_address_confirmation_scope() -> None:
    execution = make_engine().run(
        Context("sim"),
        scopes=["global", "delivery.address-preview"],
        trace_attributes={"conversation_id": "conversation-1"},
    )

    assert execution.decision is not None
    assert isinstance(execution.decision.effect, ConfirmAddress)
    assert execution.decision.rule_id == "confirm-address"
    assert evaluated_rules(execution) == ["cancel-order", "confirm-address"]
    assert "confirm-order" not in evaluated_rules(execution)
    assert execution.trace.attributes["conversation_id"] == "conversation-1"


def test_global_cancel_intercepts_active_address_scope() -> None:
    execution = make_engine().run(
        Context("cancelar pedido"),
        scopes=["global", "delivery.address-preview"],
    )

    assert execution.decision is not None
    assert isinstance(execution.decision.effect, CancelOrder)
    assert evaluated_rules(execution) == ["cancel-order"]


def test_invalid_address_answer_reasks_without_order_fallback() -> None:
    execution = make_engine().run(
        Context("talvez"),
        scopes=["global", "delivery.address-preview", "order.confirmation"],
    )

    assert execution.decision is not None
    assert execution.decision.outcome.value == "reask"
    assert execution.decision.rule_id == "confirm-address"
    assert evaluated_rules(execution) == ["cancel-order", "confirm-address"]


def test_trace_explains_complete_execution() -> None:
    execution = make_engine().run(
        Context("sim"),
        scopes=["global", "delivery.address-preview"],
    )

    names = [event.name for event in execution.trace.events]
    assert names[0] == "execution.started"
    assert "scope.entered" in names
    assert "rule.evaluated" in names
    assert "resolution.completed" in names
    assert "effect.proposed" in names
    assert names[-1] == "execution.completed"
    assert execution.trace.status == "completed"
    assert [event.sequence for event in execution.trace.events] == list(
        range(1, len(execution.trace.events) + 1)
    )

