"""Rule normalization and validation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from policyflow.core.exceptions import InvalidRuleError

from .decorator import RULE_METADATA_ATTRIBUTE
from .definition import RuleCallable, RuleDefinition, RuleMetadata


def normalize_rule(
    candidate: object,
    *,
    registration_order: int,
) -> RuleDefinition[Any, Any]:
    """Convert a decorated function or structural rule object to a definition."""
    metadata = getattr(candidate, RULE_METADATA_ATTRIBUTE, None)
    if isinstance(metadata, RuleMetadata) and callable(candidate):
        return RuleDefinition(
            rule_id=metadata.rule_id,
            evaluate=cast(RuleCallable[Any, Any], candidate),
            priority=metadata.priority,
            tags=metadata.tags,
            registration_order=registration_order,
        )

    evaluate = getattr(candidate, "evaluate", None)
    rule_id = getattr(candidate, "rule_id", None)
    if not isinstance(rule_id, str) or not rule_id.strip() or not callable(evaluate):
        raise InvalidRuleError(
            "rules must be decorated functions or objects with rule_id and evaluate()"
        )

    priority = getattr(candidate, "priority", 100)
    if isinstance(priority, bool) or not isinstance(priority, int):
        raise InvalidRuleError(f"rule {rule_id!r} priority must be an integer")

    tags = getattr(candidate, "tags", {})
    if not isinstance(tags, dict):
        try:
            tags = dict(tags)
        except (TypeError, ValueError) as exc:
            raise InvalidRuleError(f"rule {rule_id!r} tags must be a mapping") from exc

    return RuleDefinition(
        rule_id=rule_id,
        evaluate=cast(Callable[..., Any], evaluate),
        priority=priority,
        tags=tags,
        registration_order=registration_order,
    )

