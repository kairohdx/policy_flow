"""Collect multiple validation issues from one imported spreadsheet row."""

from dataclasses import dataclass

from policyflow import CollectAll, PolicyEngine, RuleResult, rule


@dataclass(frozen=True, slots=True)
class EmployeeRow:
    registration: str
    cpf: str
    department: str
    workload: int


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    field: str
    code: str
    message: str


@rule(id="validate-registration", priority=10)
def validate_registration(row: EmployeeRow) -> RuleResult[ValidationIssue]:
    if row.registration.strip():
        return RuleResult.pass_(reason="registration_present")
    return RuleResult.block(
        ValidationIssue(
            field="registration",
            code="required",
            message="Registration is required.",
        ),
        reason="registration_missing",
    )


@rule(id="validate-cpf", priority=20)
def validate_cpf(row: EmployeeRow) -> RuleResult[ValidationIssue]:
    digits = "".join(character for character in row.cpf if character.isdigit())
    if len(digits) == 11:
        return RuleResult.pass_(reason="cpf_shape_valid")
    return RuleResult.block(
        ValidationIssue(
            field="cpf",
            code="invalid",
            message="CPF must contain 11 digits.",
        ),
        reason="cpf_shape_invalid",
    )


@rule(id="validate-department", priority=30)
def validate_department(row: EmployeeRow) -> RuleResult[ValidationIssue]:
    if row.department in {"finance", "operations", "people"}:
        return RuleResult.pass_(reason="department_known")
    return RuleResult.block(
        ValidationIssue(
            field="department",
            code="unknown",
            message="Department is not registered.",
        ),
        reason="department_unknown",
    )


@rule(id="validate-workload", priority=40)
def validate_workload(row: EmployeeRow) -> RuleResult[ValidationIssue]:
    if row.workload in {20, 30, 40}:
        return RuleResult.pass_(reason="workload_allowed")
    return RuleResult.block(
        ValidationIssue(
            field="workload",
            code="invalid",
            message="Workload must be 20, 30, or 40 hours.",
        ),
        reason="workload_invalid",
    )


def build_engine() -> PolicyEngine[EmployeeRow, ValidationIssue]:
    engine = PolicyEngine[EmployeeRow, ValidationIssue](name="employee-import")
    engine.add_scope(
        "employee.validation",
        rules=[
            validate_registration,
            validate_cpf,
            validate_department,
            validate_workload,
        ],
        strategy=CollectAll(),
    )
    return engine


if __name__ == "__main__":
    execution = build_engine().run(
        EmployeeRow(
            registration="",
            cpf="123",
            department="unknown",
            workload=15,
        ),
        scopes=["employee.validation"],
    )

    for decision in execution.decisions:
        issue = decision.effect
        if issue is not None:
            print(f"{issue.field}: {issue.message}")

