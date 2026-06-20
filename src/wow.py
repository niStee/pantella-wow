import json
import time
import os
from .base_interface import BaseGameInterface

try:
    import win32gui
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("[WARN] pywin32 not available. EditBox scraping will not work.")

class WoWGameInterface(BaseGameInterface):
    def __init__(self, conversation_manager):
        super().__init__(conversation_manager, valid_games=['wow'], interface_slug='wow')
        self.wow_window = None
        self.editbox_hwnd = None
        self.combat_log_path = self._find_combat_log()
        self.combat_log_offset = 0
        self.combat_events = []

    def _find_combat_log(self):
        paths = [
            r"C:\Program Files (x86)\World of Warcraft\_retail_\Logs\WoWCombatLog.txt",
            r"C:\Program Files\World of Warcraft\_retail_\Logs\WoWCombatLog.txt",
            r"C:\Program Files (x86)\World of Warcraft\_classic_\Logs\WoWCombatLog.txt",
        ]
        for p in paths:
            if os.path.exists(p):
                return p
        return None

    def _find_wow_window(self):
        if not WIN32_AVAILABLE:
            return None
        self.wow_window = win32gui.FindWindow("GxWindowClass", None)
        if not self.wow_window:
            return None

        def enum_child(hwnd, extra):
            if win32gui.GetClassName(hwnd) == "Edit":
                if win32gui.GetWindowText(hwnd) == "MantellaWoW_State":
                    self.editbox_hwnd = hwnd
                    return False
            return True

        win32gui.EnumChildWindows(self.wow_window, enum_child, None)
        return self.editbox_hwnd

    def _read_editbox_text(self):
        if not WIN32_AVAILABLE or not self.editbox_hwnd:
            self.editbox_hwnd = self._find_wow_window()
            if not self.editbox_hwnd:
                return None
        try:
            length = win32gui.SendMessage(self.editbox_hwnd, win32con.WM_GETTEXTLENGTH, 0, 0)
            if length == 0:
                return None
            buffer = win32gui.PyMakeBuffer(length + 1)
            win32gui.SendMessage(self.editbox_hwnd, win32con.WM_GETTEXT, length + 1, buffer)
            return str(buffer, 'utf-8').strip('\x00')
        except Exception as e:
            print(f"[ERROR] Failed to read EditBox: {e}")
            self.editbox_hwnd = None
            return None

    def _poll_combat_log(self):
        if not self.combat_log_path or not os.path.exists(self.combat_log_path):
            return
        try:
            with open(self.combat_log_path, 'r', encoding='utf-8') as f:
                if self.combat_log_offset == 0:
                    f.seek(0, 2)
                    self.combat_log_offset = f.tell()
                    return
                f.seek(self.combat_log_offset)
                lines = f.readlines()
                self.combat_log_offset = f.tell()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if 'SPELL_CAST_SUCCESS' in line or 'UNIT_DIED' in line:
                        self.combat_events.append(line)
                        if len(self.combat_events) > 5:
                            self.combat_events.pop(0)
        except Exception as e:
            print(f"[ERROR] Combat log read failed: {e}")

    def load_game_state(self):
        state = {}
        text = self._read_editbox_text()
        if text:
            try:
                state = json.loads(text)
            except json.JSONDecodeError:
                state = {"raw_state": text[:500]}
        self._poll_combat_log()
        if self.combat_events:
            state['combat_events'] = self.combat_events[-5:]
        self.game_state = state
        return state

    def get_current_context_string(self):
        state = self.load_game_state()
        ctx_parts = []
        if 'player_name' in state:
            ctx_parts.append(f"Player: {state['player_name']} (Level {state.get('player_level', '?')})")
        if 'zone' in state:
            ctx_parts.append(f"Zone: {state['zone']}")
        if 'in_combat' in state:
            ctx_parts.append(f"Combat: {'Yes' if state['in_combat'] else 'No'}")
        if 'active_quests' in state and isinstance(state['active_quests'], list):
            quests = state['active_quests'][:3]
            ctx_parts.append(f"Active Quests: {', '.join(q.get('name', '?') for q in quests)}")
        if 'dbm_timers' in state and isinstance(state['dbm_timers'], list):
            timers = state['dbm_timers'][:3]
            ctx_parts.append(f"Boss Timers: {', '.join(t.get('message', '?') for t in timers)}")
        if 'combat_events' in state:
            ctx_parts.append(f"Recent Combat: {len(state['combat_events'])} events")
        return '\n'.join(ctx_parts)

    def is_conversation_ended(self):
        state = self.load_game_state()
        return not state.get('player_name') and self.editbox_hwnd is not None
