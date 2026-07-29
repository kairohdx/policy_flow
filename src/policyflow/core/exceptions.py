"""Public PolicyFlow exceptions."""


class PolicyFlowError(Exception):
    """Base class for package errors."""


class ConfigurationError(PolicyFlowError):
    """Raised when an engine, scope, or rule is configured incorrectly."""


class DuplicateScopeError(ConfigurationError):
    """Raised when an existing scope is registered again."""


class DuplicateRuleError(ConfigurationError):
    """Raised when a rule id is duplicated within one scope."""


class ScopeNotFoundError(ConfigurationError):
    """Raised when execution references an unknown scope."""


class InvalidRuleError(ConfigurationError):
    """Raised when an object cannot be normalized as a rule."""


class InvalidRuleResultError(PolicyFlowError):
    """Raised when a rule does not return RuleResult."""


class AsyncRuleInSyncExecutionError(PolicyFlowError):
    """Raised when run() encounters an asynchronous rule."""

