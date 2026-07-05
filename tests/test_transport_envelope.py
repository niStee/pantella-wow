"""Tests for the MessageEnvelope transport envelope."""

import pytest

from game_interfaces.transport.envelope import VALID_TYPES, MessageEnvelope


class TestMessageEnvelopeFromRaw:
    """Tests for MessageEnvelope.from_raw()."""

    def test_happy_path_minimal(self):
        """Minimal valid combat_log envelope."""
        env = MessageEnvelope.from_raw(
            {
                "version": 1,
                "channel": "combat_log",
                "sequence": 1,
                "timestamp_ms": 1780000000000,
                "type": "event",
                "payload": {"event": "COMBAT_LOG_EVENT_UNFILTERED"},
            }
        )
        assert env.version == 1
        assert env.channel == "combat_log"
        assert env.sequence == 1
        assert env.timestamp_ms == 1780000000000
        assert env.type == "event"
        assert env.payload == {"event": "COMBAT_LOG_EVENT_UNFILTERED"}
        assert env.checksum is None

    def test_happy_path_with_checksum(self):
        """Pixel transport with required checksum."""
        env = MessageEnvelope.from_raw(
            {
                "version": 1,
                "channel": "pixel",
                "sequence": 42,
                "timestamp_ms": 1780000000000,
                "type": "state_delta",
                "payload": {"health": 80},
                "checksum": "a1b2c3d4",
            }
        )
        assert env.checksum == "a1b2c3d4"

    def test_happy_path_saved_variables(self):
        """SavedVariables transport with snapshot type."""
        env = MessageEnvelope.from_raw(
            {
                "version": 1,
                "channel": "saved_variables",
                "sequence": 0,
                "timestamp_ms": 1780000000000,
                "type": "snapshot",
                "payload": {"config": {"tts_enabled": True}},
            }
        )
        assert env.channel == "saved_variables"
        assert env.type == "snapshot"

    def test_happy_path_all_types(self):
        """All valid types are accepted."""
        for t in VALID_TYPES:
            env = MessageEnvelope.from_raw(
                {
                    "version": 1,
                    "channel": "combat_log",
                    "sequence": 1,
                    "timestamp_ms": 1780000000000,
                    "type": t,
                    "payload": {},
                }
            )
            assert env.type == t

    def test_extra_fields_filtered(self):
        """Extra fields in raw dict are not stored."""
        env = MessageEnvelope.from_raw(
            {
                "version": 1,
                "channel": "combat_log",
                "sequence": 1,
                "timestamp_ms": 1780000000000,
                "type": "event",
                "payload": {},
                "extra_field": "should_not_appear",
            }
        )
        assert not hasattr(env, "extra_field")

    def test_health_type_with_empty_payload(self):
        """Health type with an empty payload is valid."""
        env = MessageEnvelope.from_raw(
            {
                "version": 1,
                "channel": "combat_log",
                "sequence": 5,
                "timestamp_ms": 1780000000000,
                "type": "health",
                "payload": {},
            }
        )
        assert env.type == "health"

    # --- Failure paths ---

    def test_invalid_channel(self):
        """Invalid channel raises ValueError."""
        with pytest.raises(ValueError, match="Invalid channel"):
            MessageEnvelope.from_raw(
                {
                    "version": 1,
                    "channel": "tcp_socket",
                    "sequence": 1,
                    "timestamp_ms": 1780000000000,
                    "type": "event",
                    "payload": {},
                }
            )

    def test_invalid_type(self):
        """Invalid type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid type"):
            MessageEnvelope.from_raw(
                {
                    "version": 1,
                    "channel": "combat_log",
                    "sequence": 1,
                    "timestamp_ms": 1780000000000,
                    "type": "ping",
                    "payload": {},
                }
            )

    def test_invalid_version(self):
        """Version != 1 raises ValueError."""
        with pytest.raises(ValueError, match="version"):
            MessageEnvelope.from_raw(
                {
                    "version": 2,
                    "channel": "combat_log",
                    "sequence": 1,
                    "timestamp_ms": 1780000000000,
                    "type": "event",
                    "payload": {},
                }
            )

    def test_version_not_int(self):
        """Non-int version raises ValueError."""
        with pytest.raises(ValueError, match="version"):
            MessageEnvelope.from_raw(
                {
                    "version": "one",
                    "channel": "combat_log",
                    "sequence": 1,
                    "timestamp_ms": 1780000000000,
                    "type": "event",
                    "payload": {},
                }
            )

    def test_negative_timestamp(self):
        """Negative timestamp_ms raises ValueError."""
        with pytest.raises(ValueError, match="timestamp_ms"):
            MessageEnvelope.from_raw(
                {
                    "version": 1,
                    "channel": "combat_log",
                    "sequence": 1,
                    "timestamp_ms": -1,
                    "type": "event",
                    "payload": {},
                }
            )

    def test_zero_timestamp(self):
        """Zero timestamp_ms raises ValueError."""
        with pytest.raises(ValueError, match="timestamp_ms"):
            MessageEnvelope.from_raw(
                {
                    "version": 1,
                    "channel": "combat_log",
                    "sequence": 1,
                    "timestamp_ms": 0,
                    "type": "event",
                    "payload": {},
                }
            )

    def test_negative_sequence(self):
        """Negative sequence raises ValueError."""
        with pytest.raises(ValueError, match="sequence"):
            MessageEnvelope.from_raw(
                {
                    "version": 1,
                    "channel": "combat_log",
                    "sequence": -1,
                    "timestamp_ms": 1780000000000,
                    "type": "event",
                    "payload": {},
                }
            )

    def test_payload_not_dict(self):
        """Non-dict payload raises ValueError."""
        with pytest.raises(ValueError, match="payload"):
            MessageEnvelope.from_raw(
                {
                    "version": 1,
                    "channel": "combat_log",
                    "sequence": 1,
                    "timestamp_ms": 1780000000000,
                    "type": "event",
                    "payload": "not_a_dict",
                }
            )

    def test_missing_required_field(self):
        """Missing required field raises KeyError."""
        with pytest.raises(KeyError, match="version"):
            MessageEnvelope.from_raw(
                {
                    "channel": "combat_log",
                    "sequence": 1,
                    "timestamp_ms": 1780000000000,
                    "type": "event",
                    "payload": {},
                }
            )

    def test_channel_empty_string(self):
        """Empty channel string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid channel"):
            MessageEnvelope.from_raw(
                {
                    "version": 1,
                    "channel": "",
                    "sequence": 1,
                    "timestamp_ms": 1780000000000,
                    "type": "event",
                    "payload": {},
                }
            )

    def test_type_empty_string(self):
        """Empty type string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid type"):
            MessageEnvelope.from_raw(
                {
                    "version": 1,
                    "channel": "combat_log",
                    "sequence": 1,
                    "timestamp_ms": 1780000000000,
                    "type": "",
                    "payload": {},
                }
            )


class TestMessageEnvelopeToDict:
    """Tests for MessageEnvelope.to_dict()."""

    def test_roundtrip(self):
        """to_dict() returns the same fields as the input."""
        raw = {
            "version": 1,
            "channel": "combat_log",
            "sequence": 1,
            "timestamp_ms": 1780000000000,
            "type": "event",
            "payload": {"key": "value"},
        }
        env = MessageEnvelope.from_raw(raw)
        result = env.to_dict()
        assert result == raw

    def test_with_checksum_roundtrip(self):
        """to_dict() includes checksum when present."""
        raw = {
            "version": 1,
            "channel": "pixel",
            "sequence": 7,
            "timestamp_ms": 1780000000000,
            "type": "state_delta",
            "payload": {"x": 1},
            "checksum": "deadbeef",
        }
        env = MessageEnvelope.from_raw(raw)
        assert env.to_dict() == raw

    def test_omits_none_checksum(self):
        """to_dict() omits checksum when it is None."""
        env = MessageEnvelope.from_raw(
            {
                "version": 1,
                "channel": "combat_log",
                "sequence": 1,
                "timestamp_ms": 1780000000000,
                "type": "event",
                "payload": {},
            }
        )
        result = env.to_dict()
        assert "checksum" not in result


class TestMessageEnvelopeValidate:
    """Tests for explicit MessageEnvelope.validate()."""

    def test_valid_envelope_passes(self):
        """A valid combat_log envelope passes validate()."""
        env = MessageEnvelope.from_raw(
            {
                "version": 1,
                "channel": "combat_log",
                "sequence": 1,
                "timestamp_ms": 1780000000000,
                "type": "event",
                "payload": {},
            }
        )
        assert env.validate() is None

    def test_pixel_without_checksum_fails_on_validate(self):
        """Pixel transport without checksum raises ValueError via validate()."""
        env = MessageEnvelope(
            version=1,
            channel="pixel",
            sequence=1,
            timestamp_ms=1780000000000,
            type="state_delta",
            payload={},
        )
        with pytest.raises(ValueError, match="checksum.*required.*pixel"):
            env.validate()

    def test_pixel_with_checksum_passes(self):
        """Pixel transport with checksum passes validate()."""
        env = MessageEnvelope.from_raw(
            {
                "version": 1,
                "channel": "pixel",
                "sequence": 1,
                "timestamp_ms": 1780000000000,
                "type": "state_delta",
                "payload": {},
                "checksum": "abc123",
            }
        )
        assert env.validate() is None

    def test_combat_log_validation_optional(self):
        """Pixel-specific checks are not enforced on other channels."""
        env = MessageEnvelope(
            version=1,
            channel="combat_log",
            sequence=1,
            timestamp_ms=1780000000000,
            type="event",
            payload={},
            checksum="present_but_optional",
        )
        assert env.validate() is None


class TestMessageEnvelopeDirectConstruction:
    """Tests for constructing MessageEnvelope directly via the dataclass."""

    def test_direct_construction(self):
        """Direct dataclass construction works."""
        env = MessageEnvelope(
            version=1,
            channel="combat_log",
            sequence=1,
            timestamp_ms=1780000000000,
            type="event",
            payload={},
        )
        assert env.version == 1

    def test_direct_construction_all_fields(self):
        """Direct construction with all fields."""
        env = MessageEnvelope(
            version=1,
            channel="pixel",
            sequence=99,
            timestamp_ms=1780000000000,
            type="health",
            payload={"hp": 50},
            checksum="xyz789",
        )
        assert env.checksum == "xyz789"
