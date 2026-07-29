"""Produce multiple independent CRM actions from one customer message."""

from dataclasses import dataclass
import re

from policyflow import CollectAll, PolicyEngine, RuleResult, rule

_PHONE_PATTERN = re.compile(r"\b(\d{10,11})\b")


@dataclass(frozen=True, slots=True)
class CrmMessage:
    customer_id: str
    text: str


@dataclass(frozen=True, slots=True)
class UpdatePhone:
    customer_id: str
    phone: str


@dataclass(frozen=True, slots=True)
class AddInterestTag:
    customer_id: str
    tag: str


@dataclass(frozen=True, slots=True)
class CreateSalesTask:
    customer_id: str
    title: str


CrmEffect = UpdatePhone | AddInterestTag | CreateSalesTask


@rule(id="capture-phone", priority=10, tags={"domain": "contact"})
def capture_phone(message: CrmMessage) -> RuleResult[CrmEffect]:
    match = _PHONE_PATTERN.search(message.text)
    if match is None:
        return RuleResult.pass_(reason="phone_not_found")
    return RuleResult.consume(
        UpdatePhone(message.customer_id, match.group(1)),
        reason="phone_found",
    )


@rule(id="detect-enterprise-interest", priority=20, tags={"domain": "sales"})
def detect_enterprise_interest(message: CrmMessage) -> RuleResult[CrmEffect]:
    normalized = message.text.lower()
    if "plano empresarial" not in normalized:
        return RuleResult.pass_(reason="enterprise_interest_not_found")
    return RuleResult.consume(
        AddInterestTag(message.customer_id, "enterprise"),
        reason="enterprise_interest_found",
    )


@rule(id="request-sales-contact", priority=30, tags={"domain": "sales"})
def request_sales_contact(message: CrmMessage) -> RuleResult[CrmEffect]:
    normalized = message.text.lower()
    if "falar com vendedor" not in normalized:
        return RuleResult.pass_(reason="sales_contact_not_requested")
    return RuleResult.consume(
        CreateSalesTask(message.customer_id, "Contact interested customer"),
        reason="sales_contact_requested",
    )


def build_engine() -> PolicyEngine[CrmMessage, CrmEffect]:
    engine = PolicyEngine[CrmMessage, CrmEffect](name="crm-message")
    engine.add_scope(
        "crm.message-policies",
        rules=[
            capture_phone,
            detect_enterprise_interest,
            request_sales_contact,
        ],
        strategy=CollectAll(),
    )
    return engine


if __name__ == "__main__":
    execution = build_engine().run(
        CrmMessage(
            customer_id="customer-42",
            text=(
                "Meu telefone é 11987654321, tenho interesse no plano "
                "empresarial e quero falar com vendedor."
            ),
        ),
        scopes=["crm.message-policies"],
    )

    for decision in execution.decisions:
        print(f"{decision.rule_id}: {decision.effect!r}")

