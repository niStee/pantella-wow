"""Integration tests for the end-to-end combat log transport pipeline.

Validates the full round-trip: simulated WoW combat-log addon-message lines
(written in the format ``SendAddonMessageLogged`` produces) are written to a
temp file, consumed by ``CombatLogTransport``, and emitted as validated
``MessageEnvelope`` instances with the expected field values.
"""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path

import pytest

from game_interfaces.transport.combat_log import CombatLogTransport
from game_interfaces.transport.envelope import MessageEnvelope

CANONICAL_LINE = (
    "7/5 12:00:00.123  CHAT_MSG_ADDON: PANTELLA Player "
    '{"version":1,"type":"state_delta","payload":{"pet_name":"Boo"}}'
)


async def _collect(
    transport: CombatLogTransport,
    *,
    expected: int = 1,
    timeout_s: float = 1.0,
) -> list[MessageEnvelope]:
    """Collect up to ``expected`` envelopes from ``transport.read()``.

    Because ``read()`` is an infinite polling loop, we stop as soon as we have
    enough envelopes or the timeout expires.
    """
    envelopes: list[MessageEnvelope] = []

    async def _drain() -> None:
        async for env in transport.read():
            envelopes.append(env)
            if len(envelopes) >= expected:
                break

    with contextlib.suppress(asyncio.TimeoutError):
        await asyncio.wait_for(_drain(), timeout=timeout_s)
    return envelopes


class TestCombatLogIntegration:
    """End-to-end round-trip tests for CombatLogTransport."""

    @pytest.mark.asyncio
    async def test_single_message_round_trip(self, tmp_path: Path) -> None:
        """Write one PANTELLA line and verify all envelope fields."""
        log_path = tmp_path / "WoWCombatLog.txt"
        transport = CombatLogTransport(log_path, poll_interval_s=0.05)
        await transport.start()
        try:
            # Write the line *after* start() so seek-to-end skips it
            # initially; the polling loop picks it up on the next iteration.
            log_path.write_text(CANONICAL_LINE + "\n", encoding="utf-8")
            envelopes = await _collect(transport, expected=1, timeout_s=1.0)

            assert len(envelopes) == 1
            env = envelopes[0]

            assert env.version == 1
            assert env.channel == "combat_log"
            assert env.type == "state_delta"
            assert env.sequence == 1
            assert env.timestamp_ms > 0
            assert env.checksum is None
            assert env.payload == {"pet_name": "Boo"}
        finally:
            await transport.stop()

    @pytest.mark.asyncio
    async def test_three_messages_sequential(self, tmp_path: Path) -> None:
        """Write 3 messages and assert sequences 1, 2, 3."""
        log_path = tmp_path / "WoWCombatLog.txt"
        transport = CombatLogTransport(log_path, poll_interval_s=0.05)
        await transport.start()
        try:
            lines = [
                CANONICAL_LINE,
                CANONICAL_LINE.replace("pet_name", "pet_name2"),
                CANONICAL_LINE.replace("pet_name", "pet_name3"),
            ]
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            envelopes = await _collect(transport, expected=3, timeout_s=1.0)

            assert len(envelopes) == 3
            assert envelopes[0].sequence == 1
            assert envelopes[1].sequence == 2
            assert envelopes[2].sequence == 3

            # Payloads should differ because we swapped pet_name keys
            assert envelopes[0].payload == {"pet_name": "Boo"}
            assert envelopes[1].payload == {"pet_name2": "Boo"}
            assert envelopes[2].payload == {"pet_name3": "Boo"}

            # Timestamps should be monotonic
            assert (
                envelopes[0].timestamp_ms <= envelopes[1].timestamp_ms <= envelopes[2].timestamp_ms
            )
        finally:
            await transport.stop()

    @pytest.mark.asyncio
    async def test_non_matching_lines_ignored(self, tmp_path: Path) -> None:
        """Regular combat log lines without PANTELLA are filtered out."""
        log_path = tmp_path / "WoWCombatLog.txt"
        transport = CombatLogTransport(log_path, poll_interval_s=0.05)
        await transport.start()
        try:
            log_path.write_text(
                "7/5 12:00:00.100  COMBAT_LOG_EVENT: SPELL_DAMAGE,Player-1-DeadlyBossMods,"
                "0x0000000000000001,Player-1-Target,0x0000000000000002,100\n"
                + CANONICAL_LINE
                + "\n",
                encoding="utf-8",
            )
            envelopes = await _collect(transport, expected=1, timeout_s=1.0)

            assert len(envelopes) == 1
            assert envelopes[0].type == "state_delta"
            assert envelopes[0].payload == {"pet_name": "Boo"}
        finally:
            await transport.stop()
