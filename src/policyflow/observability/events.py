"""Immutable execution event types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Mapping

from policyflow.typing import JsonValue


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    name: str
    timestamp: datetime
    trace_id: str
    execution_id: str
    sequence: int
    duration_ms: float | None = None
    attributes: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))

