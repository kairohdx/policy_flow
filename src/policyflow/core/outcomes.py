"""Possible outcomes returned by a rule."""

from enum import Enum


class RuleOutcome(str, Enum):
    """Control-flow meaning of a rule evaluation."""

    CONSUME = "consume"
    REASK = "reask"
    PASS = "pass"
    BLOCK = "block"

    @property
    def terminal(self) -> bool:
        """Whether FirstMatch should stop after this outcome."""
        return self is not RuleOutcome.PASS

