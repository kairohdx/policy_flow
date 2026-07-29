"""Trace correlation context."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TraceContext:
    trace_id: str
    correlation_id: str | None = None
    parent_execution_id: str | None = None

    def __post_init__(self) -> None:
        if not self.trace_id.strip():
            raise ValueError("trace_id cannot be empty")

