"""Completed execution traces."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Mapping

from policyflow.typing import JsonValue

from .events import ExecutionEvent


@dataclass(frozen=True, slots=True)
class ExecutionTrace:
    trace_id: str
    execution_id: str
    pipeline: str
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    status: str
    events: tuple[ExecutionEvent, ...]
    attributes: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))

