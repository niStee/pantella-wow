"""Combat-log transport for the Pantella-WoW IPC layer.

This module tails ``WoWCombatLog.txt`` and yields :class:`MessageEnvelope`
instances for lines whose payload is prefixed with ``PANTELLA`` (the addon
prefix used by ``C_ChatInfo.SendAddonMessageLogged``).

The transport uses a simple async polling loop to avoid cross-thread and
``asyncio``/``watchdog`` integration issues. File rotation is detected by
comparing the current file size with the last-known offset: if the file
shrinks or is replaced, ingestion restarts from the beginning of the new file.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from game_interfaces.transport.base import BaseTransport, TransportHealth
from game_interfaces.transport.envelope import MessageEnvelope

logger = logging.getLogger(__name__)


class CombatLogTransport(BaseTransport):
    """Tails ``WoWCombatLog.txt`` and yields ``MessageEnvelope`` instances.

    The parser extracts the JSON payload from lines that look like:
        ``7/5 12:00:00.123  CHAT_MSG_ADDON: PANTELLA Player {"version":1,...}``

    Everything after the third whitespace-delimited field (``PANTELLA``) is
    treated as the raw envelope JSON.

    Attributes:
        log_path: Path to the WoW combat log file to tail.
        poll_interval_s: Seconds between file polls while running.
    """

    def __init__(self, log_path: str | Path, poll_interval_s: float = 0.1) -> None:
        self.log_path = Path(log_path)
        self.poll_interval_s = poll_interval_s
        self._running = False
        self._offset = 0
        self._sequence = 0
        self._last_message_ts: int | None = None
        self._last_error: str | None = None

    async def start(self) -> None:
        """Begin tailing the combat log file."""
        self._running = True
        self._offset = 0
        self._last_error = None
        if self.log_path.exists():
            self._offset = self.log_path.stat().st_size
        else:
            self._last_error = f"Combat log file not found: {self.log_path}"
            logger.warning(self._last_error)

    async def stop(self) -> None:
        """Stop tailing the combat log file."""
        self._running = False

    def read(self) -> AsyncIterator[MessageEnvelope]:
        """Yield validated ``MessageEnvelope`` instances as new lines arrive.

        The returned async generator is independent of the underlying polling
        loop: each iteration polls once and yields any new lines found.
        """
        return self._read_loop()

    async def _read_loop(self) -> AsyncIterator[MessageEnvelope]:
        while self._running:
            if not self.log_path.exists():
                self._last_error = f"Combat log file not found: {self.log_path}"
                await asyncio.sleep(self.poll_interval_s)
                continue

            try:
                current_size = self.log_path.stat().st_size
            except OSError as exc:
                self._last_error = f"Cannot stat combat log: {exc}"
                logger.warning(self._last_error)
                await asyncio.sleep(self.poll_interval_s)
                continue

            self._last_error = None

            if current_size < self._offset:
                # File rotated/replaced; start from the beginning.
                self._offset = 0

            if current_size > self._offset:
                try:
                    with self.log_path.open(encoding="utf-8", errors="replace") as fh:
                        fh.seek(self._offset)
                        lines = fh.readlines()
                        self._offset = fh.tell()
                except OSError as exc:
                    self._last_error = f"Cannot read combat log: {exc}"
                    logger.warning(self._last_error)
                    await asyncio.sleep(self.poll_interval_s)
                    continue

                for line in lines:
                    envelope = self._parse_line(line)
                    if envelope is not None:
                        yield envelope

            await asyncio.sleep(self.poll_interval_s)

    def _parse_line(self, line: str) -> MessageEnvelope | None:
        """Parse a single combat log line into a ``MessageEnvelope``.

        Returns ``None`` if the line is not a ``PANTELLA`` line or cannot be
        parsed. Logs a warning for malformed JSON.

        The canonical line shape is::

            7/5 12:00:00.123  CHAT_MSG_ADDON: PANTELLA Player {"version":1,...}

        We locate the ``PANTELLA`` token and parse the JSON object that
        follows it, ignoring the intermediate "Player" field. This is robust
        to whitespace variation in the combat-log prefix.
        """
        stripped = line.strip()
        if not stripped:
            return None

        if "PANTELLA" not in stripped:
            return None

        json_start = stripped.find("{")
        if json_start == -1:
            return None

        json_payload = stripped[json_start:]
        try:
            raw: dict[str, Any] = json.loads(json_payload)
        except json.JSONDecodeError as exc:
            logger.warning("Malformed JSON in combat log: %s", exc)
            return None

        if not isinstance(raw, dict):
            logger.warning("Combat log payload is not a JSON object: %r", raw)
            return None

        # The Lua addon emits only the inner envelope fields (version, type,
        # payload). The Python backend assigns channel, sequence and timestamp.
        now_ms = int(time.time() * 1000)
        self._sequence += 1
        self._last_message_ts = now_ms

        try:
            return MessageEnvelope.from_raw(
                {
                    "version": raw["version"],
                    "channel": "combat_log",
                    "sequence": self._sequence,
                    "timestamp_ms": now_ms,
                    "type": raw["type"],
                    "payload": raw.get("payload", {}),
                    "checksum": None,
                }
            )
        except KeyError as exc:
            logger.warning("Combat log payload missing required field: %s", exc)
            return None
        except ValueError as exc:
            logger.warning("Invalid combat log envelope: %s", exc)
            return None

    def health(self) -> TransportHealth:
        """Return the current transport health."""
        if not self._running:
            return TransportHealth(
                channel="combat_log",
                status="unavailable",
                error=self._last_error or "transport not started",
            )
        if self._last_error is not None:
            return TransportHealth(
                channel="combat_log",
                status="degraded",
                last_message_ts=self._last_message_ts,
                error=self._last_error,
            )
        return TransportHealth(
            channel="combat_log",
            status="active",
            last_message_ts=self._last_message_ts,
        )
