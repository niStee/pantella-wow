import os
import time
import json
import pyperclip
from .base_interface import BaseGameInterface

class WoWGameInterface(BaseGameInterface):
    """Reads WoW state from Clipboard and CombatLog and maps to Pantella format."""

    def __init__(self, conversation_manager):
        super().__init__(conversation_manager, valid_games=['wow'], interface_slug='wow')
        self.wow_account = self._find_wow_account()
        # Find Logs directory which is a sibling to WTF
        self.wow_root = os.path.dirname(os.path.dirname(self.wow_account))
        self.combat_log_file = os.path.join(self.wow_root, 'Logs', 'WoWCombatLog.txt')
        self.save_file = os.path.join(
            self.wow_account, 'SavedVariables', 'MantellaWoW.lua'
        )
        self.last_modified = 0
        self.last_clipboard_text = ""
        self.combat_log_pos = 0
        self.recent_combat_events = []
        
        # Seek to the end of combat log on init
        if os.path.exists(self.combat_log_file):
            self.combat_log_pos = os.path.getsize(self.combat_log_file)
            
        # Initial load from SavedVariables for persistence
        self._load_saved_variables()

    def _find_wow_account(self):
        """Find WoW WTF directory. Supports Retail and Classic."""
        wow_paths = [
            os.path.expandvars(r'%PROGRAMFILES(X86)%\World of Warcraft\_retail_\WTF\Account'),
            os.path.expandvars(r'%PROGRAMFILES(X86)%\World of Warcraft\_classic_\WTF\Account'),
            os.path.expandvars(r'%PROGRAMFILES(X86)%\World of Warcraft\_classic_era_\WTF\Account'),
            os.path.expandvars(r'%PROGRAMFILES%\World of Warcraft\_retail_\WTF\Account'),
            os.path.expandvars(r'%PROGRAMFILES%\World of Warcraft\_classic_\WTF\Account'),
            # Linux via Wine/Proton
            os.path.expanduser('~/.wine/drive_c/Program Files/World of Warcraft/_retail_/WTF/Account'),
            os.path.expanduser('~/.wine/drive_c/Program Files/World of Warcraft/_classic_/WTF/Account'),
        ]

        for path in wow_paths:
            if os.path.exists(path):
                # Find the first account folder
                accounts = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
                if accounts:
                    return os.path.join(path, accounts[0])

        # Default fallback
        return os.path.expanduser('~/WoW/WTF/Account/ACCOUNTNAME')

    def _load_saved_variables(self):
        """Read MantellaWoW.lua SavedVariables for initial persistent state."""
        if not os.path.exists(self.save_file):
            return
        try:
            with open(self.save_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Basic JSON extraction if stored as string
        except (IOError, OSError):
            pass

    def _poll_combat_log(self):
        """Tail the WoWCombatLog.txt for new combat events."""
        if not os.path.exists(self.combat_log_file):
            return

        current_size = os.path.getsize(self.combat_log_file)
        if current_size < self.combat_log_pos:
            # File was truncated/rolled over
            self.combat_log_pos = 0

        if current_size == self.combat_log_pos:
            return

        try:
            with open(self.combat_log_file, 'r', encoding='utf-8') as f:
                f.seek(self.combat_log_pos)
                new_data = f.read()
                self.combat_log_pos = f.tell()
                
                # Keep last 5 significant events
                for line in new_data.split('\n'):
                    if not line.strip(): continue
                    # Basic filter for interesting events
                    if "SPELL_CAST_SUCCESS" in line or "UNIT_DIED" in line:
                        self.recent_combat_events.append(line.strip())
                
                # Keep list small
                if len(self.recent_combat_events) > 5:
                    self.recent_combat_events = self.recent_combat_events[-5:]
        except (IOError, OSError):
            pass

    def load_game_state(self):
        """Read state from clipboard and combat log."""
        self._poll_combat_log()
        
        try:
            clipboard_text = pyperclip.paste()
            if clipboard_text and clipboard_text.startswith("MANTELLA:"):
                if clipboard_text != self.last_clipboard_text:
                    self.last_clipboard_text = clipboard_text
                    json_str = clipboard_text[9:]  # Remove prefix
                    try:
                        self.game_state.update(json.loads(json_str))
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass
            
        return self.game_state

    def get_current_context_string(self):
        """Build context string for LLM prompt."""
        state = self.load_game_state()

        ctx_parts = []

        if 'player_name' in state:
            ctx_parts.append(f"Player: {state['player_name']} (Level {state.get('player_level', '?')})")

        if 'zone' in state:
            ctx_parts.append(f"Zone: {state['zone']}")

        if 'in_combat' in state:
            ctx_parts.append(f"Combat: {'Yes' if state['in_combat'] else 'No'}")

        if 'active_quests' in state:
            quests = state['active_quests']
            quest_names = []
            for q in quests:
                if isinstance(q, dict) and 'name' in q:
                    quest_names.append(q['name'])
            if quest_names:
                ctx_parts.append(f"Active Quests: {', '.join(quest_names[:3])}")

        if 'dbm_timers' in state:
            timers = state['dbm_timers']
            timer_msgs = []
            for t in timers:
                if isinstance(t, dict) and 'message' in t:
                    timer_msgs.append(f"{t['message']} ({t.get('time_remaining', 0)}s)")
            if timer_msgs:
                ctx_parts.append(f"Boss Timers: {', '.join(timer_msgs[:3])}")

        if 'recent_deaths' in state:
            ctx_parts.append(f"Recent Encounter Deaths: {state['recent_deaths']}")
            
        if self.recent_combat_events:
            ctx_parts.append("Recent Combat Log Events:")
            for event in self.recent_combat_events:
                # Truncate long combat log lines for context
                ctx_parts.append(f" - {event[:100]}...")

        return '\n'.join(ctx_parts)

    def is_conversation_ended(self):
        """Check if player logged out."""
        state = self.load_game_state()
        return not state.get('player_name')
