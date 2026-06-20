import pytest
import sys
from unittest.mock import MagicMock

# Mock Windows-only modules before any import
win32gui_mock = MagicMock()
win32con_mock = MagicMock()
winsound_mock = MagicMock()

sys.modules['win32gui'] = win32gui_mock
sys.modules['win32con'] = win32con_mock
sys.modules['winsound'] = winsound_mock

# Mock tkinter for headless CI
tkinter_mock = MagicMock()
sys.modules['tkinter'] = tkinter_mock

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
    cm.valid_games = ['wow']
    return cm
