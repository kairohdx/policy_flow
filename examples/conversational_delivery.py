"""Contextual ownership example inspired by an address confirmation flow."""

from dataclasses import dataclass

from policyflow import FirstMatch, PolicyEngine, RuleResult, rule


@dataclass(frozen=True, slots=True)
class TurnContext:
    message: str


@dataclass(frozen=True, slots=True)
class ConfirmAddress:
    pass


@dataclass(frozen=True, slots=True)
class ConfirmOrder:
    pass


@dataclass(frozen=True, slots=True)
class CancelOrder:
    pass


TurnEffect = ConfirmAddress | ConfirmOrder | CancelOrder


@rule(id="cancel-order", priority=10, tags={"kind": "global"})
def cancel_order(ctx: TurnContext) -> RuleResult[TurnEffect]:
    if ctx.message.lower() != "cancelar pedido":
        return RuleResult.pass_(reason="cancel_signal_not_found")
    return RuleResult.consume(CancelOrder(), reason="cancel_signal_detected")


@rule(id="confirm-address")
def confirm_address(ctx: TurnContext) -> RuleResult[TurnEffect]:
    if ctx.message.lower() != "sim":
        return RuleResult.reask(reason="address_confirmation_required")
    return RuleResult.consume(ConfirmAddress(), reason="address_confirmed")


@rule(id="confirm-order")
def confirm_order(ctx: TurnContext) -> RuleResult[TurnEffect]:
    if ctx.message.lower() != "sim":
        return RuleResult.reask(reason="order_confirmation_required")
    return RuleResult.consume(ConfirmOrder(), reason="order_confirmed")


def build_engine() -> PolicyEngine[TurnContext, TurnEffect]:
    engine = PolicyEngine[TurnContext, TurnEffect](name="checkout-turn")
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


if __name__ == "__main__":
    execution = build_engine().run(
        TurnContext("sim"),
        scopes=["global", "delivery.address-preview"],
    )
    assert execution.decision is not None
    print(type(execution.decision.effect).__name__)
    print([event.name for event in execution.trace.events])

