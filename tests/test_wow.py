import pytest
from unittest.mock import MagicMock, patch, PropertyMock

# wow.py imports BaseGameInterface which might need mocking
# We'll import after conftest mocks are set
from game_interfaces.wow import WoWGameInterface


class TestPromptBuilding:
    """Test get_system_prompt() personality assignment."""
    
    @pytest.fixture
    def interface(self, mock_conversation_manager):
        with patch('game_interfaces.wow.WIN32_AVAILABLE', True):
            with patch('game_interfaces.wow.WATCHDOG_AVAILABLE', False):
                with patch('game_interfaces.wow.WINSOUND_AVAILABLE', True):
                    iface = WoWGameInterface(mock_conversation_manager)
                    # Mock the overlay to avoid tkinter issues
                    iface.overlay = MagicMock()
                    return iface
    
    def test_voidwalker_personality(self, interface):
        interface.game_state = {
            'pet': {
                'name': 'Kraggore',
                'family': 'Voidwalker',
                'pet_token': 'PET',
                'health': 100,
                'is_dead': False
            },
            'zone': 'Elwynn Forest'
        }
        prompt = interface.get_system_prompt()
        assert 'Kraggore' in prompt
        assert 'sarcastic' in prompt.lower()
        assert 'Elwynn Forest' in prompt
        
    def test_mount_personality(self, interface):
        interface.game_state = {
            'pet': {
                'name': 'Swift Purple Raptor',
                'family': 'Mount',
                'pet_token': 'MOUNT',
                'health': 100,
                'is_dead': False
            },
            'zone': 'Durotar'
        }
        prompt = interface.get_system_prompt()
        assert 'Swift Purple Raptor' in prompt
        assert 'steed' in prompt.lower() or 'mount' in prompt.lower()
        
    def test_mount_sub_personality_drake(self, interface):
        interface.game_state = {
            'pet': {
                'name': 'Obsidian Worldbreaker',
                'family': 'Mount',
                'pet_token': 'MOUNT',
                'health': 100,
                'is_dead': False
            },
            'zone': 'Stormwind'
        }
        prompt = interface.get_system_prompt()
        assert 'drake' in prompt.lower() or 'dragon' in prompt.lower()
        
    def test_vanity_pet_personality(self, interface):
        interface.game_state = {
            'pet': {
                'name': 'Lil\' Ragnaros',
                'family': 'Companion',
                'pet_token': 'COMPANION',
                'health': 100,
                'is_dead': False
            },
            'zone': 'Orgrimmar'
        }
        prompt = interface.get_system_prompt()
        assert 'Lil\' Ragnaros' in prompt or 'Lil' in prompt
        assert 'cute' in prompt.lower() or 'curious' in prompt.lower()
        
    def test_low_health_status(self, interface):
        interface.game_state = {
            'pet': {
                'name': 'Wolf',
                'family': 'Wolf',
                'pet_token': 'PET',
                'health': 15,
                'is_dead': False
            },
            'zone': 'Westfall'
        }
        prompt = interface.get_system_prompt()
        assert 'exhausted' in prompt.lower() or 'struggling' in prompt.lower()
        
    def test_dead_pet_status(self, interface):
        interface.game_state = {
            'pet': {
                'name': 'Voidwalker',
                'family': 'Voidwalker',
                'pet_token': 'PET',
                'health': 0,
                'is_dead': True
            },
            'zone': 'Deadwind Pass'
        }
        prompt = interface.get_system_prompt()
        assert 'unsummoned' in prompt.lower() or 'resting' in prompt.lower()


class TestRadiantTriggers:
    """Test check_radiant_triggers() event detection."""
    
    @pytest.fixture
    def interface(self, mock_conversation_manager):
        with patch('game_interfaces.wow.WIN32_AVAILABLE', True):
            with patch('game_interfaces.wow.WATCHDOG_AVAILABLE', False):
                with patch('game_interfaces.wow.WINSOUND_AVAILABLE', True):
                    iface = WoWGameInterface(mock_conversation_manager)
                    iface.overlay = MagicMock()
                    iface.last_pet_health = 100
                    iface.last_zone = "Elwynn Forest"
                    iface.last_dbm_timers = {}
                    iface.pet_was_dead = False
                    return iface
    
    def test_critical_health_trigger(self, interface):
        interface.game_state = {
            'pet': {'name': 'Wolf', 'family': 'Wolf', 'health': 20, 'is_dead': False}
        }
        triggers = interface.check_radiant_triggers()
        assert len(triggers) > 0
        assert any(t['priority'] == 'urgent' for t in triggers)
        assert any('dying' in t['text'] or 'cannot hold' in t['text'] for t in triggers)
        
    def test_pet_death_trigger(self, interface):
        interface.game_state = {
            'pet': {'name': 'Voidwalker', 'family': 'Voidwalker', 'health': 0, 'is_dead': True}
        }
        triggers = interface.check_radiant_triggers()
        assert any(t['priority'] == 'urgent' for t in triggers)
        assert any('Aargh' in t['text'] or 'died' in t['text'] for t in triggers)
        
    def test_no_duplicate_triggers(self, interface):
        """Same health should not trigger twice."""
        interface.game_state = {
            'pet': {'name': 'Wolf', 'family': 'Wolf', 'health': 20, 'is_dead': False}
        }
        t1 = interface.check_radiant_triggers()
        t2 = interface.check_radiant_triggers()
        assert len(t1) > 0
        assert len(t2) == 0  # Already triggered at 20%


class TestStateParsing:
    """Test load_game_state() and edge cases."""
    
    @pytest.fixture
    def interface(self, mock_conversation_manager):
        with patch('game_interfaces.wow.WIN32_AVAILABLE', False):
            with patch('game_interfaces.wow.WATCHDOG_AVAILABLE', False):
                with patch('game_interfaces.wow.WINSOUND_AVAILABLE', True):
                    iface = WoWGameInterface(mock_conversation_manager)
                    iface.overlay = MagicMock()
                    return iface
    
    def test_malformed_json_fallback(self, interface):
        with patch.object(interface, '_read_editbox_text', return_value='{not valid json'):
            state = interface.load_game_state()
            assert 'raw_state' in state
            
    def test_empty_state(self, interface):
        with patch.object(interface, '_read_editbox_text', return_value=None):
            state = interface.load_game_state()
            assert isinstance(state, dict)


class TestPantellaAPICompliance:
    """Test that all required methods exist and don't crash."""
    
    @pytest.fixture
    def interface(self, mock_conversation_manager):
        with patch('game_interfaces.wow.WIN32_AVAILABLE', False):
            with patch('game_interfaces.wow.WATCHDOG_AVAILABLE', False):
                with patch('game_interfaces.wow.WINSOUND_AVAILABLE', True):
                    iface = WoWGameInterface(mock_conversation_manager)
                    iface.overlay = MagicMock()
                    return iface
    
    def test_enable_character_selection(self, interface):
        result = interface.enable_character_selection()
        assert isinstance(result, list)
        
    def test_end_conversation(self, interface):
        interface.radiant_queue = ['test']
        result = interface.end_conversation()
        assert result is True
        assert len(interface.radiant_queue) == 0
        
    def test_remove_from_conversation(self, interface):
        result = interface.remove_from_conversation('test')
        assert result is True
        
    def test_queue_actor_method(self, interface):
        result = interface.queue_actor_method('npc', 'wave')
        assert result is True
        
    def test_is_conversation_ended(self, interface):
        interface.game_state = {'player_name': ''}
        interface.editbox_hwnd = 1
        assert interface.is_conversation_ended() is True
        
    def test_get_current_context_string(self, interface):
        interface.game_state = {
            'player_name': 'Player',
            'player_level': 60,
            'zone': 'Stormwind',
            'pet': {'name': 'Wolf', 'family': 'Wolf', 'health': 100}
        }
        ctx = interface.get_current_context_string()
        assert 'Player' in ctx
        assert 'Stormwind' in ctx
        assert 'Wolf' in ctx
