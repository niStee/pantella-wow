"""Tests for the CombatLogTransport channel.

The canonical log line fixture is:
    7/5 12:00:00.123  CHAT_MSG_ADDON: PANTELLA Player {"version":1,...}

We parse by extracting the JSON object that follows the ``PANTELLA`` token.
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


class TestCombatLogTransportLifecycle:
    """Start/stop/health behavior."""

    @pytest.mark.asyncio
    async def test_start_stop_sets_running_state(self, tmp_path: Path) -> None:
        log_path = tmp_path / "WoWCombatLog.txt"
        transport = CombatLogTransport(log_path)
        assert not transport._running
        await transport.start()
        assert transport._running
        await transport.stop()
        assert not transport._running

    def test_health_before_start_reports_unavailable(self, tmp_path: Path) -> None:
        transport = CombatLogTransport(tmp_path / "missing.txt")
        health = transport.health()
        assert health.channel == "combat_log"
        assert health.status == "unavailable"
        assert health.error is not None

    @pytest.mark.asyncio
    async def test_health_after_start_no_file_is_degraded(self, tmp_path: Path) -> None:
        transport = CombatLogTransport(tmp_path / "missing.txt")
        await transport.start()
        try:
            health = transport.health()
            assert health.status == "degraded"
            assert health.error is not None
            assert "not found" in health.error.lower() or "missing" in health.error.lower()
        finally:
            await transport.stop()

    @pytest.mark.asyncio
    async def test_health_after_start_with_file_is_active(self, tmp_path: Path) -> None:
        log_path = tmp_path / "WoWCombatLog.txt"
        log_path.write_text("", encoding="utf-8")
        transport = CombatLogTransport(log_path)
        await transport.start()
        try:
            health = transport.health()
            assert health.status == "active"
            assert health.error is None
        finally:
            await transport.stop()


class TestCombatLogTransportParsing:
    """Parsing and envelope generation."""

    @pytest.mark.asyncio
    async def test_read_yields_pantella_envelope(self, tmp_path: Path) -> None:
        log_path = tmp_path / "WoWCombatLog.txt"
        transport = CombatLogTransport(log_path, poll_interval_s=0.05)
        await transport.start()
        try:
            log_path.write_text(CANONICAL_LINE + "\n", encoding="utf-8")
            envelopes = await _collect(transport, expected=1, timeout_s=1.0)

            assert len(envelopes) == 1
            assert isinstance(envelopes[0], MessageEnvelope)
            assert envelopes[0].channel == "combat_log"
            assert envelopes[0].type == "state_delta"
            assert envelopes[0].payload == {"pet_name": "Boo"}
            assert envelopes[0].version == 1
            assert envelopes[0].checksum is None
            assert envelopes[0].sequence == 1
            assert envelopes[0].timestamp_ms > 0
        finally:
            await transport.stop()

    @pytest.mark.asyncio
    async def test_python_assigned_sequence_and_timestamp(self, tmp_path: Path) -> None:
        log_path = tmp_path / "WoWCombatLog.txt"
        transport = CombatLogTransport(log_path, poll_interval_s=0.05)
        await transport.start()
        try:
            log_path.write_text(
                CANONICAL_LINE + "\n" + CANONICAL_LINE.replace("pet_name", "pet_name2") + "\n",
                encoding="utf-8",
            )
            envelopes = await _collect(transport, expected=2, timeout_s=1.0)

            assert len(envelopes) == 2
            assert envelopes[0].sequence == 1
            assert envelopes[1].sequence == 2
            assert envelopes[0].timestamp_ms <= envelopes[1].timestamp_ms
        finally:
            await transport.stop()

    @pytest.mark.asyncio
    async def test_ignores_non_pantella_lines(self, tmp_path: Path) -> None:
        log_path = tmp_path / "WoWCombatLog.txt"
        transport = CombatLogTransport(log_path, poll_interval_s=0.05)
        await transport.start()
        try:
            log_path.write_text(
                "7/5 12:00:00.100  COMBAT_LOG_EVENT: SPELL_DAMAGE...\n" + CANONICAL_LINE + "\n",
                encoding="utf-8",
            )
            envelopes = await _collect(transport, expected=1, timeout_s=1.0)

            assert len(envelopes) == 1
            assert envelopes[0].type == "state_delta"
        finally:
            await transport.stop()

    @pytest.mark.asyncio
    async def test_skips_malformed_json_with_warning(self, tmp_path: Path, caplog) -> None:
        log_path = tmp_path / "WoWCombatLog.txt"
        transport = CombatLogTransport(log_path, poll_interval_s=0.05)
        await transport.start()
        try:
            log_path.write_text(
                "7/5 12:00:00.123  CHAT_MSG_ADDON: PANTELLA Player {not valid json}\n"
                + CANONICAL_LINE
                + "\n",
                encoding="utf-8",
            )
            envelopes = await _collect(transport, expected=1, timeout_s=1.0)

            assert len(envelopes) == 1
            assert "malformed" in caplog.text.lower() or "json" in caplog.text.lower()
        finally:
            await transport.stop()

    @pytest.mark.asyncio
    async def test_missing_file_gracefully_yields_nothing(self, tmp_path: Path) -> None:
        transport = CombatLogTransport(tmp_path / "does_not_exist.txt", poll_interval_s=0.05)
        await transport.start()
        try:
            envelopes = await _collect(transport, expected=1, timeout_s=0.2)
            assert envelopes == []
        finally:
            await transport.stop()

    @pytest.mark.asyncio
    async def test_file_rotation_picks_up_new_file(self, tmp_path: Path) -> None:
        log_path = tmp_path / "WoWCombatLog.txt"
        log_path.write_text(CANONICAL_LINE + "\n", encoding="utf-8")
        transport = CombatLogTransport(log_path, poll_interval_s=0.05)
        await transport.start()
        try:
            appended_line = (
                "7/5 12:00:00.500  CHAT_MSG_ADDON: PANTELLA Player "
                '{"version":1,"type":"event","payload":{"event":"HEAL"}}'
            )
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(appended_line + "\n")
            envelopes = await _collect(transport, expected=1, timeout_s=1.0)
            assert len(envelopes) == 1
            assert envelopes[0].type == "event"
            assert envelopes[0].payload == {"event": "HEAL"}

            rotated_line = (
                "7/5 12:00:01.000  CHAT_MSG_ADDON: PANTELLA Player "
                '{"version":1,"type":"event","payload":{"event":"DAMAGE"}}'
            )
            log_path.write_text(rotated_line + "\n", encoding="utf-8")

            found = await _collect(transport, expected=1, timeout_s=1.0)

            assert len(found) == 1
            assert found[0].type == "event"
            assert found[0].payload == {"event": "DAMAGE"}
        finally:
            await transport.stop()


class TestCombatLogTransportEdgeCases:
    """Edge cases for robustness."""

    @pytest.mark.asyncio
    async def test_empty_payload_is_valid(self, tmp_path: Path) -> None:
        log_path = tmp_path / "WoWCombatLog.txt"
        transport = CombatLogTransport(log_path, poll_interval_s=0.05)
        await transport.start()
        try:
            log_path.write_text(
                "7/5 12:00:00.123  CHAT_MSG_ADDON: PANTELLA Player "
                '{"version":1,"type":"event","payload":{}}\n',
                encoding="utf-8",
            )
            envelopes = await _collect(transport, expected=1, timeout_s=1.0)

            assert len(envelopes) == 1
            assert envelopes[0].payload == {}
        finally:
            await transport.stop()

    @pytest.mark.asyncio
    async def test_payload_without_required_envelope_fields_warns(
        self, tmp_path: Path, caplog
    ) -> None:
        log_path = tmp_path / "WoWCombatLog.txt"
        transport = CombatLogTransport(log_path, poll_interval_s=0.05)
        await transport.start()
        try:
            log_path.write_text(
                "7/5 12:00:00.123  CHAT_MSG_ADDON: PANTELLA Player "
                '{"version":1,"payload":{"x":1}}\n',
                encoding="utf-8",
            )
            envelopes = await _collect(transport, expected=1, timeout_s=0.5)

            assert envelopes == []
            assert "missing" in caplog.text.lower() or "required" in caplog.text.lower()
        finally:
            await transport.stop()

    @pytest.mark.asyncio
    async def test_stop_exhausts_read_iterator(self, tmp_path: Path) -> None:
        log_path = tmp_path / "WoWCombatLog.txt"
        log_path.write_text(CANONICAL_LINE + "\n", encoding="utf-8")
        transport = CombatLogTransport(log_path)
        await transport.start()
        await transport.stop()

        envelopes = [env async for env in transport.read()]
        assert envelopes == []
