"""Pantella-WoW transport layer — channel-neutral message envelope and interface."""

from game_interfaces.transport.base import BaseTransport, TransportHealth
from game_interfaces.transport.combat_log import CombatLogTransport
from game_interfaces.transport.envelope import (
    VALID_CHANNELS,
    VALID_TYPES,
    MessageEnvelope,
)

__all__ = [
    "BaseTransport",
    "CombatLogTransport",
    "MessageEnvelope",
    "TransportHealth",
    "VALID_CHANNELS",
    "VALID_TYPES",
]
