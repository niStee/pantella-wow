from src.conversation_managers.base_conversation_manager import BaseConversationManager

class WowConversationManager(BaseConversationManager):
    """
    Pantella addon conversation manager for World of Warcraft.
    Handles radiant queue (urgent in-game events) before normal LLM turn.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_radiant_idx = 0
    
    def step(self):
        # Process urgent radiant triggers BEFORE the normal LLM step
        if hasattr(self.game_interface, 'radiant_queue') and self.game_interface.radiant_queue:
            urgent_text = self.game_interface.radiant_queue.pop(0)
            
            # Speak immediately via TTS
            voices = self.synthesizer.voices()
            if voices:
                import random
                self.synthesizer._say(urgent_text, random.choice(voices))
            
            # Update overlay if available
            if hasattr(self.game_interface, '_update_overlay'):
                self.game_interface._update_overlay(urgent_text, 'red')
            
            # We processed one urgent message this tick. 
            # Skip LLM turn this tick to not block on generating normal responses
            return
        
        # Normal flow: let base manager handle microphone/input/LLM
        super().step()
