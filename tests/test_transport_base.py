"""Tests for the BaseTransport abstract interface and TransportHealth dataclass."""

import pytest

from game_interfaces.transport.base import BaseTransport, TransportHealth
from game_interfaces.transport.envelope import MessageEnvelope


class TestBaseTransportCannotInstantiate:
    """BaseTransport is an ABC — cannot be instantiated directly."""

    def test_cannot_instantiate_base_transport(self):
        """Direct instantiation of BaseTransport raises TypeError."""
        with pytest.raises(TypeError):
            BaseTransport()  # type: ignore[abstract]


class TestFakeTransport:
    """FakeTransport (in tests/conftest.py) implements all abstract methods."""

    @pytest.mark.asyncio
    async def test_read_yields_envelope(self, fake_transport):
        """fake_transport fixture yields at least one MessageEnvelope."""
        await fake_transport.start()
        envelopes = []
        async for env in fake_transport.read():
            envelopes.append(env)
        assert len(envelopes) >= 1
        assert isinstance(envelopes[0], MessageEnvelope)

    @pytest.mark.asyncio
    async def test_read_returns_correct_envelope_fields(self, fake_transport):
        """Envelope from fake_transport has expected field values."""
        await fake_transport.start()
        async for env in fake_transport.read():
            assert env.version == 1
            assert env.channel == "combat_log"
            assert env.sequence == 1
            assert env.timestamp_ms == 1780000000000
            assert env.type == "event"
            assert env.payload == {"event": "COMBAT_LOG_EVENT_UNFILTERED"}
            break

    @pytest.mark.asyncio
    async def test_read_multiple_envelopes(self, fake_transport):
        """FakeTransport can yield multiple envelopes via seed()."""
        fake_transport.seed(
            MessageEnvelope(
                version=1,
                channel="combat_log",
                sequence=2,
                timestamp_ms=1780000000001,
                type="event",
                payload={"event": "DAMAGE_SHIELD"},
            )
        )
        await fake_transport.start()
        envelopes = [env async for env in fake_transport.read()]
        assert len(envelopes) == 2
        assert envelopes[0].sequence == 1
        assert envelopes[1].sequence == 2

    @pytest.mark.asyncio
    async def test_read_empty_when_not_started(self, fake_transport):
        """read() yields nothing when start() has not been called."""
        envelopes = [env async for env in fake_transport.read()]
        assert len(envelopes) == 0

    def test_health_after_start(self, fake_transport):
        """health() returns active after start()."""
        import asyncio

        asyncio.run(fake_transport.start())
        health = fake_transport.health()
        assert health.status == "active"
        assert health.channel == "combat_log"

    def test_health_before_start(self, fake_transport):
        """health() returns unavailable before start()."""
        health = fake_transport.health()
        assert health.status == "unavailable"


class TestTransportHealthDataclass:
    """TransportHealth dataclass construction and defaults."""

    def test_minimal_construction(self):
        """TransportHealth can be constructed with only required args."""
        h = TransportHealth(channel="combat_log", status="active")
        assert h.channel == "combat_log"
        assert h.status == "active"
        assert h.last_message_ts is None
        assert h.error is None

    def test_full_construction(self):
        """TransportHealth accepts all fields."""
        h = TransportHealth(
            channel="pixel",
            status="degraded",
            last_message_ts=1780000000000,
            error="high latency",
        )
        assert h.channel == "pixel"
        assert h.status == "degraded"
        assert h.last_message_ts == 1780000000000
        assert h.error == "high latency"

    def test_unavailable_status(self):
        """unavailable status with error message."""
        h = TransportHealth(
            channel="combat_log",
            status="unavailable",
            error="file not found",
        )
        assert h.status == "unavailable"
        assert h.error == "file not found"
