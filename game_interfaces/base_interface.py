# Base Game Interface (from Pantella architecture)
# This is a minimal stub based on the Pantella project structure.
# The full project is at: https://github.com/Pathos14489/Pantella

class BaseGameInterface:
    def __init__(self, conversation_manager, valid_games=None, interface_slug=None):
        self.conversation_manager = conversation_manager
        self.valid_games = valid_games or []
        self.interface_slug = interface_slug
        self.game_state = {}

    def load_game_state(self):
        """Override in subclass. Read game state from source."""
        raise NotImplementedError

    def get_current_location(self, presume=''):
        """Return current player location."""
        return self.game_state.get('location', presume)

    def get_current_game_time(self):
        """Return current in-game time."""
        return self.game_state.get('game_time', 'Unknown')

    def send_response(self, sentence_queue, event=None):
        """Send response via TTS."""
        pass

    def get_player_response(self, possible_names_list=None):
        """Get player input via STT or text."""
        return None

    def is_conversation_ended(self):
        """Check if conversation has ended."""
        return False

    def get_current_context_string(self):
        """Return context string for LLM prompt."""
        return str(self.game_state)
