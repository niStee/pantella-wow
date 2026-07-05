"""Pantella-WoW transport layer — channel-neutral message envelope."""

from game_interfaces.transport.envelope import (
    VALID_CHANNELS,
    VALID_TYPES,
    MessageEnvelope,
)

__all__ = [
    "MessageEnvelope",
    "VALID_CHANNELS",
    "VALID_TYPES",
]
