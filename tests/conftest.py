import sys
from unittest.mock import MagicMock

import pytest

# Mock Windows-only modules before any import
win32gui_mock = MagicMock()
win32con_mock = MagicMock()
winsound_mock = MagicMock()

sys.modules["win32gui"] = win32gui_mock
sys.modules["win32con"] = win32con_mock
sys.modules["winsound"] = winsound_mock

# Mock tkinter for headless CI
tkinter_mock = MagicMock()
sys.modules["tkinter"] = tkinter_mock

# Mock Pantella main repo imports
src_mock = MagicMock()
src_gi_mock = MagicMock()
src_gi_base_mock = MagicMock()


class DummyBaseInterface:
    def __init__(self, *args, **kwargs):
        pass


src_gi_base_mock.BaseGameInterface = DummyBaseInterface
sys.modules["src"] = src_mock
sys.modules["src.game_interfaces"] = src_gi_mock
sys.modules["src.game_interfaces.base_interface"] = src_gi_base_mock


@pytest.fixture
def mock_win32gui():
    win32gui_mock.reset_mock()
    return win32gui_mock


@pytest.fixture
def mock_win32con():
    win32con_mock.reset_mock()
    return win32con_mock


@pytest.fixture
def mock_winsound():
    winsound_mock.reset_mock()
    return winsound_mock


@pytest.fixture
def mock_conversation_manager():
    cm = MagicMock()
    cm.valid_games = ["wow"]
    return cm


# ---------------------------------------------------------------------------
# Transport test utilities
# ---------------------------------------------------------------------------

from collections.abc import AsyncIterator as _AsyncIterator  # noqa: E402

from game_interfaces.transport.base import BaseTransport, TransportHealth  # noqa: E402
from game_interfaces.transport.envelope import MessageEnvelope  # noqa: E402


class FakeTransport(BaseTransport):
    """A minimal in-memory transport for testing.

    Yields envelopes from an in-memory queue and reports ``active`` health.
    """

    def __init__(self, channel: str = "combat_log") -> None:
        self._channel = channel
        self._messages: list[MessageEnvelope] = []
        self._envelopes: list[MessageEnvelope] = []
        self._running = False

    def seed(self, envelope: MessageEnvelope) -> None:
        """Add an envelope to the queue that ``read()`` will yield."""
        self._envelopes.append(envelope)

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def read(self) -> _AsyncIterator[MessageEnvelope]:
        if not self._running:
            return
        # Yield all seeded envelopes, then stop
        for env in self._envelopes:
            yield env
        self._envelopes.clear()

    def health(self) -> TransportHealth:
        return TransportHealth(
            channel=self._channel,
            status="active" if self._running else "unavailable",
        )


@pytest.fixture
def fake_transport() -> FakeTransport:
    """Return a started :class:`FakeTransport` seeded with one envelope."""
    t = FakeTransport()
    t.seed(
        MessageEnvelope(
            version=1,
            channel="combat_log",
            sequence=1,
            timestamp_ms=1780000000000,
            type="event",
            payload={"event": "COMBAT_LOG_EVENT_UNFILTERED"},
        )
    )
    return t
