"""Typed contextual policy execution."""

from .core import (
    AsyncRuleInSyncExecutionError,
    ConfigurationError,
    Decision,
    DuplicateRuleError,
    DuplicateScopeError,
    Execution,
    InvalidRuleError,
    InvalidRuleResultError,
    PolicyEngine,
    PolicyFlowError,
    RuleOutcome,
    RuleResult,
    ScopeNotFoundError,
)
from .observability import (
    AsyncEventSink,
    EventSink,
    ExecutionEvent,
    ExecutionTrace,
    TraceContext,
)
from .rules import Rule, rule
from .strategies import FirstMatch, ResolutionStrategy

__all__ = [
    "AsyncEventSink",
    "AsyncRuleInSyncExecutionError",
    "ConfigurationError",
    "Decision",
    "DuplicateRuleError",
    "DuplicateScopeError",
    "EventSink",
    "Execution",
    "ExecutionEvent",
    "ExecutionTrace",
    "FirstMatch",
    "InvalidRuleError",
    "InvalidRuleResultError",
    "PolicyEngine",
    "PolicyFlowError",
    "ResolutionStrategy",
    "Rule",
    "RuleOutcome",
    "RuleResult",
    "ScopeNotFoundError",
    "TraceContext",
    "rule",
]

