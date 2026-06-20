import pytest
import time
from unittest.mock import MagicMock, patch

from game_interfaces.overlay import TkinterOverlay


class TestOverlay:
    @pytest.fixture
    def overlay(self):
        with patch('game_interfaces.overlay.tk.Tk'):
            with patch('game_interfaces.overlay.tk.Frame'):
                with patch('game_interfaces.overlay.tk.Label'):
                    o = TkinterOverlay(title="TestCompanion", width=400, height=120)
                    return o
    
    def test_update_text_queues_message(self, overlay):
        overlay.update_text("Hello World", "white")
        assert not overlay.msg_queue.empty()
        msg, color = overlay.msg_queue.get()
        assert msg == "Hello World"
        assert color == "white"
        
    def test_update_title_changes_attribute(self, overlay):
        overlay.update_title("NewName")
        assert overlay.title == "NewName"
        
    def test_stop_sets_running_false(self, overlay):
        overlay._running = True
        overlay.root = MagicMock()
        overlay.stop()
        assert overlay._running is False
