"""
MemoryConsolidator — Phase 1 consolidation triggers.

The consolidator subscribes to broadcast events (e.g. from a
GlobalWorkspaceBroadcaster) and gates memory writes through a salience
threshold.  Every ``sync_event`` arriving on the broadcast bus becomes a
write opportunity; only atoms whose salience meets or exceeds the threshold
are consolidated into long-term storage.

This satisfies the same design constraint as the echo-agent-loop's
``tickInProgress`` guard: **slow consolidation must not block the next
perception cycle**.  The consolidator therefore runs each write in the
background via ``asyncio.create_task``, and drops overlapping consolidation
runs rather than queuing them (re-entrancy guard).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional

log = logging.getLogger(__name__)

# Type alias for async write callables
WriteCallback = Callable[..., Awaitable[Any]]


class MemoryConsolidator:
    """Gate memory writes through a salience threshold.

    Parameters
    ----------
    write_fn:
        An async callable that performs the actual memory write.  It is
        called with the broadcast payload as its sole positional argument.
    salience_threshold:
        Minimum salience score (0.0–1.0) required for a payload to trigger
        a write.  Payloads below the threshold are silently dropped.
    """

    def __init__(
        self,
        write_fn: WriteCallback,
        salience_threshold: float = 0.5,
    ) -> None:
        if not (0.0 <= salience_threshold <= 1.0):
            raise ValueError(
                f"salience_threshold must be in [0.0, 1.0], got {salience_threshold!r}"
            )
        self._write_fn = write_fn
        self._salience_threshold = salience_threshold
        self._consolidation_in_progress: bool = False
        self._overrun_count: int = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def salience_threshold(self) -> float:
        """The minimum salience score required to trigger a write."""
        return self._salience_threshold

    @property
    def overrun_count(self) -> int:
        """Number of broadcast events dropped due to an in-progress consolidation."""
        return self._overrun_count

    async def on_broadcast(self, payload: dict[str, Any]) -> None:
        """Handle an incoming broadcast event.

        The payload is expected to contain a ``salience`` key (float).  If
        the salience is below the configured threshold the event is dropped.
        If a consolidation is already in progress the event is also dropped
        (cooperative re-entrancy guard) and the overrun counter is incremented.
        """
        salience: float = float(payload.get("salience", 0.0))
        if salience < self._salience_threshold:
            log.debug(
                "MemoryConsolidator: dropping event with salience %.3f < threshold %.3f",
                salience,
                self._salience_threshold,
            )
            return

        if self._consolidation_in_progress:
            self._overrun_count += 1
            log.debug(
                "MemoryConsolidator: consolidation already in progress, dropping event "
                "(overrun #%d)",
                self._overrun_count,
            )
            return

        # Fire-and-forget — do not await so callers are not blocked.
        asyncio.create_task(self._run_consolidation(payload))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_consolidation(self, payload: dict[str, Any]) -> None:
        """Execute the write callback under the re-entrancy guard."""
        self._consolidation_in_progress = True
        try:
            await self._write_fn(payload)
        except Exception:
            log.exception("MemoryConsolidator: write_fn raised an exception")
        finally:
            self._consolidation_in_progress = False

    # ------------------------------------------------------------------
    # Convenience factory
    # ------------------------------------------------------------------

    @classmethod
    def from_memories_table(
        cls,
        user_id: str,
        memories_table: Any,
        salience_threshold: float = 0.5,
        default_memory_type: Optional[str] = None,
    ) -> "MemoryConsolidator":
        """Return a consolidator wired to a :class:`MemoriesTable` instance.

        Each broadcast payload that passes the salience gate will insert a
        new memory atom.  The ``content`` key in the payload is used as the
        memory content.  ``memory_type`` may be provided in the payload or
        falls back to *default_memory_type*.

        Parameters
        ----------
        user_id:
            The owner of the memory atoms that will be created.
        memories_table:
            A ``MemoriesTable`` instance (or compatible duck-type).
        salience_threshold:
            Forwarded to the constructor.
        default_memory_type:
            Fallback memory subsystem type when the payload omits it.
        """

        async def _write(payload: dict[str, Any]) -> None:
            content: str = payload.get("content", "")
            if not content:
                log.debug("MemoryConsolidator: payload has no 'content', skipping write")
                return
            memory_type: Optional[str] = payload.get("memory_type", default_memory_type)
            await memories_table.insert_new_memory(
                user_id=user_id,
                content=content,
                memory_type=memory_type,
            )

        return cls(write_fn=_write, salience_threshold=salience_threshold)
