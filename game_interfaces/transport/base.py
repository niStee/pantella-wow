"""Channel-neutral transport interface for the Pantella-WoW IPC layer.

Every transport (combat log, SavedVariables, pixel) must implement
:class:`BaseTransport` so that the rest of the system can consume
:class:`MessageEnvelope` instances without knowing the underlying channel.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

from game_interfaces.transport.envelope import MessageEnvelope


@dataclass
class TransportHealth:
    """Health snapshot for a transport channel.

    Attributes:
        channel: The transport channel this health snapshot belongs to.
        status: Operational status.
        last_message_ts: Unix epoch milliseconds of the last successfully
            ingested message, or ``None`` if none have been received.
        error: A human-readable error description, or ``None`` when healthy.
    """

    channel: str
    status: str  # "active" | "degraded" | "unavailable"
    last_message_ts: int | None = None
    error: str | None = None


class BaseTransport(ABC):
    """Abstract base class for all Pantella-WoW transports.

    Subclasses must implement :meth:`start`, :meth:`stop`, :meth:`read`,
    and :meth:`health`.
    """

    @abstractmethod
    async def start(self) -> None:
        """Open the transport channel and begin receiving messages.

        Raises:
            RuntimeError: If the transport cannot be opened.
        """

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully close the transport channel."""

    @abstractmethod
    def read(self) -> AsyncIterator[MessageEnvelope]:
        """Yield validated :class:`MessageEnvelope` instances as they arrive.

        The caller is responsible for consuming the iterator until it
        is exhausted (which typically only happens after :meth:`stop`).
        """

    @abstractmethod
    def health(self) -> TransportHealth:
        """Return a synchronous snapshot of current transport health."""
