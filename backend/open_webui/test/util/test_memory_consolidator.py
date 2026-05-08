"""
Unit tests for MemoryConsolidator (open_webui.utils.memory_consolidator).
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from open_webui.utils.memory_consolidator import MemoryConsolidator


class TestMemoryConsolidatorInit:
    def test_default_threshold(self):
        write_fn = AsyncMock()
        mc = MemoryConsolidator(write_fn)
        assert mc.salience_threshold == 0.5

    def test_custom_threshold(self):
        write_fn = AsyncMock()
        mc = MemoryConsolidator(write_fn, salience_threshold=0.8)
        assert mc.salience_threshold == 0.8

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError):
            MemoryConsolidator(AsyncMock(), salience_threshold=1.5)
        with pytest.raises(ValueError):
            MemoryConsolidator(AsyncMock(), salience_threshold=-0.1)

    def test_initial_overrun_count(self):
        mc = MemoryConsolidator(AsyncMock())
        assert mc.overrun_count == 0


class TestMemoryConsolidatorOnBroadcast:
    @pytest.mark.asyncio
    async def test_low_salience_is_dropped(self):
        write_fn = AsyncMock()
        mc = MemoryConsolidator(write_fn, salience_threshold=0.5)
        await mc.on_broadcast({"salience": 0.3, "content": "test"})
        # Allow any scheduled tasks to run
        await asyncio.sleep(0)
        write_fn.assert_not_called()

    @pytest.mark.asyncio
    async def test_high_salience_triggers_write(self):
        write_fn = AsyncMock()
        mc = MemoryConsolidator(write_fn, salience_threshold=0.5)
        await mc.on_broadcast({"salience": 0.9, "content": "hello"})
        await asyncio.sleep(0)  # let the created task run
        write_fn.assert_called_once_with({"salience": 0.9, "content": "hello"})

    @pytest.mark.asyncio
    async def test_missing_salience_defaults_to_zero(self):
        write_fn = AsyncMock()
        mc = MemoryConsolidator(write_fn, salience_threshold=0.1)
        # No 'salience' key → defaults to 0.0, which is < 0.1 → dropped
        await mc.on_broadcast({"content": "no salience key"})
        await asyncio.sleep(0)
        write_fn.assert_not_called()

    @pytest.mark.asyncio
    async def test_reentrancy_guard_drops_overlapping_event(self):
        """While a write is in progress a second event must be dropped."""
        call_count = 0
        write_started = asyncio.Event()
        write_can_finish = asyncio.Event()

        async def slow_write(payload):
            nonlocal call_count
            call_count += 1
            write_started.set()
            await write_can_finish.wait()

        mc = MemoryConsolidator(slow_write, salience_threshold=0.0)

        # Start first broadcast
        await mc.on_broadcast({"salience": 1.0, "content": "first"})
        await asyncio.sleep(0)  # let _run_consolidation start

        # Second broadcast arrives while first is still running
        await mc.on_broadcast({"salience": 1.0, "content": "second"})

        # Allow the first write to finish
        write_can_finish.set()
        await asyncio.sleep(0)

        assert call_count == 1
        assert mc.overrun_count == 1

    @pytest.mark.asyncio
    async def test_write_exception_releases_guard(self):
        """A write that raises must still release the in-progress guard."""

        async def failing_write(payload):
            raise RuntimeError("write failed")

        mc = MemoryConsolidator(failing_write, salience_threshold=0.0)
        await mc.on_broadcast({"salience": 1.0, "content": "fail"})
        await asyncio.sleep(0)

        # Guard should be released even after the exception
        assert not mc._consolidation_in_progress

    @pytest.mark.asyncio
    async def test_exact_threshold_triggers_write(self):
        """Salience equal to the threshold should trigger a write."""
        write_fn = AsyncMock()
        mc = MemoryConsolidator(write_fn, salience_threshold=0.5)
        await mc.on_broadcast({"salience": 0.5, "content": "exact"})
        await asyncio.sleep(0)
        write_fn.assert_called_once()


class TestMemoryConsolidatorFromMemoriesTable:
    @pytest.mark.asyncio
    async def test_factory_wires_insert(self):
        memories_table = MagicMock()
        memories_table.insert_new_memory = AsyncMock()

        mc = MemoryConsolidator.from_memories_table(
            user_id="user-42",
            memories_table=memories_table,
            salience_threshold=0.0,
        )

        await mc.on_broadcast({"salience": 1.0, "content": "episode one"})
        await asyncio.sleep(0)

        memories_table.insert_new_memory.assert_called_once_with(
            user_id="user-42",
            content="episode one",
            memory_type=None,
        )

    @pytest.mark.asyncio
    async def test_factory_passes_memory_type_from_payload(self):
        memories_table = MagicMock()
        memories_table.insert_new_memory = AsyncMock()

        mc = MemoryConsolidator.from_memories_table(
            user_id="user-1",
            memories_table=memories_table,
            salience_threshold=0.0,
            default_memory_type="semantic",
        )

        await mc.on_broadcast({"salience": 1.0, "content": "fact", "memory_type": "episodic"})
        await asyncio.sleep(0)

        memories_table.insert_new_memory.assert_called_once_with(
            user_id="user-1",
            content="fact",
            memory_type="episodic",
        )

    @pytest.mark.asyncio
    async def test_factory_uses_default_memory_type(self):
        memories_table = MagicMock()
        memories_table.insert_new_memory = AsyncMock()

        mc = MemoryConsolidator.from_memories_table(
            user_id="user-2",
            memories_table=memories_table,
            salience_threshold=0.0,
            default_memory_type="working",
        )

        # Payload does not specify memory_type; should fall back to "working"
        await mc.on_broadcast({"salience": 1.0, "content": "scratchpad"})
        await asyncio.sleep(0)

        memories_table.insert_new_memory.assert_called_once_with(
            user_id="user-2",
            content="scratchpad",
            memory_type="working",
        )

    @pytest.mark.asyncio
    async def test_factory_skips_empty_content(self):
        memories_table = MagicMock()
        memories_table.insert_new_memory = AsyncMock()

        mc = MemoryConsolidator.from_memories_table(
            user_id="user-3",
            memories_table=memories_table,
            salience_threshold=0.0,
        )

        await mc.on_broadcast({"salience": 1.0, "content": ""})
        await asyncio.sleep(0)

        memories_table.insert_new_memory.assert_not_called()
