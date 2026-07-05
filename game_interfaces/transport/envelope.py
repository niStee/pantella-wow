"""Normalized IPC message envelope for the Pantella-WoW transport layer.

Every transport (combat log, SavedVariables, pixel) must emit the same
logical envelope after decoding. This module provides the canonical
representation and validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

VALID_CHANNELS: set[str] = {"combat_log", "saved_variables", "pixel"}
VALID_TYPES: set[str] = {"state_delta", "event", "snapshot", "health"}
REQUIRED_FIELDS: set[str] = {
    "version",
    "channel",
    "sequence",
    "timestamp_ms",
    "type",
    "payload",
}


@dataclass
class MessageEnvelope:
    """Canonical message envelope for all WoW IPC transports.

    Attributes:
        version: Schema version. Must be 1 for the current format.
        channel: Source transport channel.
        sequence: Monotonic sequence number, assigned per-transport.
        timestamp_ms: Unix epoch milliseconds (UTC), assigned by
            the Python backend at ingest time.
        type: Message semantic type.
        payload: Message body as an arbitrary JSON-compatible dict.
        checksum: Optional integrity hash. Required for pixel transport.
    """

    version: int
    channel: str
    sequence: int
    timestamp_ms: int
    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    checksum: str | None = None

    @classmethod
    def from_raw(cls, data: dict[str, Any]) -> MessageEnvelope:
        """Create an envelope from a raw dict, applying validation.

        Args:
            data: Raw dict of envelope fields.

        Returns:
            A new MessageEnvelope instance.

        Raises:
            KeyError: If a required field is missing.
            ValueError: If any field fails validation.
        """
        for field_name in REQUIRED_FIELDS:
            if field_name not in data:
                raise KeyError(f"Missing required field: {field_name}")

        env = cls(
            version=data["version"],
            channel=data["channel"],
            sequence=data["sequence"],
            timestamp_ms=data["timestamp_ms"],
            type=data["type"],
            payload=data["payload"],
            checksum=data.get("checksum"),
        )
        env._validate_fields()
        return env

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict.

        The ``checksum`` field is omitted when ``None``.
        """
        result: dict[str, Any] = {
            "version": self.version,
            "channel": self.channel,
            "sequence": self.sequence,
            "timestamp_ms": self.timestamp_ms,
            "type": self.type,
            "payload": self.payload,
        }
        if self.checksum is not None:
            result["checksum"] = self.checksum
        return result

    def validate(self) -> None:
        """Explicitly validate envelope fields.

        This is called automatically by ``from_raw``, but is also
        available for envelopes constructed directly via the dataclass.

        Raises:
            ValueError: If any field fails validation.
        """
        self._validate_fields()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_fields(self) -> None:
        """Internal field-by-field validation (no-op if everything is OK)."""
        _validate_version(self.version)
        _validate_channel(self.channel)
        _validate_sequence(self.sequence)
        _validate_timestamp(self.timestamp_ms)
        _validate_type(self.type)
        _validate_payload(self.payload)

        if self.channel == "pixel" and self.checksum is None:
            raise ValueError("checksum is required for 'pixel' channel")


def _validate_version(value: int) -> None:
    if not isinstance(value, int) or value != 1:
        raise ValueError(f"version must be 1, got {value!r}")


def _validate_channel(value: str) -> None:
    if value not in VALID_CHANNELS:
        raise ValueError(f"Invalid channel: {value!r}. Must be one of {sorted(VALID_CHANNELS)}")


def _validate_sequence(value: int) -> None:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"sequence must be a non-negative int, got {value!r}")


def _validate_timestamp(value: int) -> None:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"timestamp_ms must be a positive int, got {value!r}")


def _validate_type(value: str) -> None:
    if value not in VALID_TYPES:
        raise ValueError(f"Invalid type: {value!r}. Must be one of {sorted(VALID_TYPES)}")


def _validate_payload(value: object) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"payload must be a dict, got {type(value).__name__}")
