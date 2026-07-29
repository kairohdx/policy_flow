from dataclasses import dataclass
import re

from policyflow import CollectAll, PolicyEngine, RuleResult, rule

_PHONE_PATTERN = re.compile(r"\b(\d{10,11})\b")


@dataclass(frozen=True)
class Message:
    lead_id: str
    text: str


@dataclass(frozen=True)
class SetPhone:
    phone: str


@dataclass(frozen=True)
class AddTag:
    tag: str


@dataclass(frozen=True)
class CreateTask:
    title: str


Effect = SetPhone | AddTag | CreateTask


@rule(id="set-phone", priority=10)
def set_phone(message: Message) -> RuleResult[Effect]:
    match = _PHONE_PATTERN.search(message.text)
    if match is None:
        return RuleResult.pass_(reason="phone_absent")
    return RuleResult.consume(SetPhone(match.group(1)), reason="phone_present")


@rule(id="tag-enterprise", priority=20)
def tag_enterprise(message: Message) -> RuleResult[Effect]:
    if "empresarial" not in message.text.lower():
        return RuleResult.pass_(reason="interest_absent")
    return RuleResult.consume(AddTag("enterprise"), reason="interest_present")


@rule(id="create-contact-task", priority=30)
def create_contact_task(message: Message) -> RuleResult[Effect]:
    if "vendedor" not in message.text.lower():
        return RuleResult.pass_(reason="contact_not_requested")
    return RuleResult.consume(
        CreateTask("Contact lead"),
        reason="contact_requested",
    )


def make_engine() -> PolicyEngine[Message, Effect]:
    engine = PolicyEngine[Message, Effect](name="crm")
    engine.add_scope(
        "crm.message",
        rules=[set_phone, tag_enterprise, create_contact_task],
        strategy=CollectAll(),
    )
    return engine


def test_one_message_can_produce_multiple_crm_actions() -> None:
    execution = make_engine().run(
        Message(
            "lead-1",
            "Telefone 11987654321, plano empresarial; quero um vendedor.",
        ),
        scopes=["crm.message"],
    )

    assert [decision.effect for decision in execution.decisions] == [
        SetPhone("11987654321"),
        AddTag("enterprise"),
        CreateTask("Contact lead"),
    ]


def test_unrelated_message_produces_no_crm_actions() -> None:
    execution = make_engine().run(
        Message("lead-2", "Obrigado pelo atendimento."),
        scopes=["crm.message"],
    )

    assert execution.decisions == ()
    evaluated = [
        event
        for event in execution.trace.events
        if event.name == "rule.evaluated"
    ]
    assert len(evaluated) == 3
    assert all(event.attributes["outcome"] == "pass" for event in evaluated)


def test_crm_trace_preserves_action_order_and_origins() -> None:
    execution = make_engine().run(
        Message("lead-3", "Plano empresarial, quero vendedor."),
        scopes=["crm.message"],
    )

    assert [decision.rule_id for decision in execution.decisions] == [
        "tag-enterprise",
        "create-contact-task",
    ]
    effect_events = [
        event
        for event in execution.trace.events
        if event.name == "effect.proposed"
    ]
    assert [event.attributes["rule_id"] for event in effect_events] == [
        "tag-enterprise",
        "create-contact-task",
    ]

