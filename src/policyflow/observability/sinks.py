"""Optional event sink contracts for future adapters."""

from __future__ import annotations

from typing import Protocol

from .events import ExecutionEvent


class EventSink(Protocol):
    def emit(self, event: ExecutionEvent) -> None:
        ...


class AsyncEventSink(Protocol):
    async def emit(self, event: ExecutionEvent) -> None:
        ...

