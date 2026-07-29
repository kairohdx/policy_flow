"""In-memory trace collection used by the execution engine."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from policyflow.typing import JsonValue

from .context import TraceContext
from .events import ExecutionEvent
from .trace import ExecutionTrace


class TraceCollector:
    """Collect ordered events and build one immutable execution trace."""

    def __init__(
        self,
        *,
        pipeline: str,
        context: TraceContext | None = None,
        attributes: Mapping[str, JsonValue] | None = None,
        id_factory: Callable[[], str] | None = None,
        wall_clock: Callable[[], datetime] | None = None,
        monotonic_clock: Callable[[], float] | None = None,
    ) -> None:
        make_id = id_factory or (lambda: uuid4().hex)
        self.pipeline = pipeline
        self.execution_id = make_id()
        self.trace_id = context.trace_id if context is not None else make_id()
        self.context = context
        self.attributes = dict(attributes or {})
        self._wall_clock = wall_clock or (lambda: datetime.now(timezone.utc))
        self._monotonic_clock = monotonic_clock or perf_counter
        self.started_at = self._wall_clock()
        self._started_tick = self._monotonic_clock()
        self._events: list[ExecutionEvent] = []

    def tick(self) -> float:
        return self._monotonic_clock()

    @staticmethod
    def elapsed_ms(started_tick: float, finished_tick: float) -> float:
        return max(0.0, (finished_tick - started_tick) * 1000)

    def emit(
        self,
        name: str,
        *,
        duration_ms: float | None = None,
        attributes: Mapping[str, JsonValue] | None = None,
    ) -> None:
        self._events.append(
            ExecutionEvent(
                name=name,
                timestamp=self._wall_clock(),
                trace_id=self.trace_id,
                execution_id=self.execution_id,
                sequence=len(self._events) + 1,
                duration_ms=duration_ms,
                attributes=attributes or {},
            )
        )

    def finish(self, status: str) -> ExecutionTrace:
        finished_tick = self._monotonic_clock()
        finished_at = self._wall_clock()
        return ExecutionTrace(
            trace_id=self.trace_id,
            execution_id=self.execution_id,
            pipeline=self.pipeline,
            started_at=self.started_at,
            finished_at=finished_at,
            duration_ms=self.elapsed_ms(self._started_tick, finished_tick),
            status=status,
            events=tuple(self._events),
            attributes=self.attributes,
        )

