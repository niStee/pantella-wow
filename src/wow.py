import json
import time
import os
import threading
from .base_interface import BaseGameInterface

try:
    import win32gui
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

class WoWGameInterface(BaseGameInterface):
    def __init__(self, conversation_manager):
        super().__init__(conversation_manager, valid_games=['wow'], interface_slug='wow')
        self.wow_window = None
        self.editbox_hwnd = None
        self.combat_log_path = self._find_combat_log()
        self.combat_log_offset = 0
        self.combat_events = []
        
        # Pet state tracking
        self.last_pet_health = 100
        self.last_zone = ""
        self.last_death_count = 0
        self.last_dbm_timers = {}
        
        # Overlay
        self.overlay = None
        self._init_overlay()
        
        # Radiant queue
        self.radiant_queue = []
        
    def _init_overlay(self):
        """Start the Tkinter overlay."""
        try:
            from .overlay import TkinterOverlay
            name = self.game_state.get('companion_name', 'Companion')
            self.overlay = TkinterOverlay(title=name)
            self.overlay.start()
        except Exception as e:
            print(f"[WARN] Overlay failed: {e}")
            
    def _update_overlay(self, text, color='white'):
        """Update overlay if available."""
        if self.overlay:
            self.overlay.update_text(text, color)
            
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
                    if 'SPELL_CAST_SUCCESS' in line or 'UNIT_DIED' in line or 'SPELL_AURA_APPLIED' in line:
                        self.combat_events.append(line)
                        if len(self.combat_events) > 5:
                            self.combat_events.pop(0)
        except Exception as e:
            print(f"[ERROR] Combat log read failed: {e}")
    
    def load_game_state(self):
        """Read state AND check for urgent radiant triggers."""
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
        
        # Check radiant triggers IMMEDIATELY after state update
        # This ensures they fire before any LLM blocking
        self._process_radiant_triggers()
        
        return state
    
    def _process_radiant_triggers(self):
        """Process radiant triggers and update overlay."""
        triggers = self.check_radiant_triggers()
        for trigger in triggers:
            # Update overlay immediately
            self._update_overlay(trigger['text'], trigger['color'])
            
            # If you want to also queue for TTS, you can set a flag
            # that the main loop reads BEFORE calling the LLM
            self.radiant_queue.append(trigger['text'])
    
    def get_system_prompt(self):
        """Build personality prompt based on pet type."""
        state = self.load_game_state()
        pet = state.get('pet', {})
        name = pet.get('name', 'Companion')
        family = pet.get('family', 'Unknown')
        health = pet.get('health', 100)
        
        personalities = {
            'Wolf': 'You are a loyal wolf companion. You speak in short, direct sentences and prioritize protecting your master.',
            'Cat': 'You are a curious cat companion. You are independent but affectionate. You notice details others miss.',
            'Bear': 'You are a stoic bear companion. You speak slowly and thoughtfully. You endure hardship without complaint.',
            'Raptor': 'You are an aggressive raptor companion. You are always eager to fight. You speak in excited bursts.',
            'Voidwalker': 'You are a sarcastic voidwalker. You serve your master grudgingly. You are darkly humorous and morbid.',
            'Imp': 'You are a hyperactive imp. You are mischievous, talk too much, and are secretly terrified of everything.',
            'Succubus': 'You are a seductive succubus. You are manipulative but deeply loyal. You speak with confidence.',
            'Felhunter': 'You are a hungry felhunter. You are obsessed with eating magic and pleasing your master. You speak in simple terms.',
            'Felguard': 'You are a disciplined felguard. You are a warrior-demon who speaks in military precision.',
            'Water Elemental': 'You are an ancient water elemental. You are cold, logical, and speak with the weight of ages.',
            'Ghoul': 'You are a feral ghoul. You are always hungry but devoted to your death knight. You speak in broken, urgent sentences.',
        }
        
        personality = personalities.get(family, 'You are a helpful companion.')
        
        if pet.get('is_dead'):
            status = 'You are currently dead/dismissed. You speak as a ghostly echo.'
        elif health < 25:
            status = 'You are critically injured. You are in pain and fear for your existence.'
        elif health < 50:
            status = 'You are wounded. You are struggling but determined.'
        else:
            status = 'You are healthy and ready.'
            
        return f"""You are {name}, {personality}
{status}
Your master is in {state.get('zone', 'an unknown place')}.
You are a real companion in World of Warcraft, not an AI assistant.
Respond in character. Keep responses under 30 seconds of speech.
Never break character. Never mention you are an AI or a program."""
    
    def check_radiant_triggers(self):
        """Check for events that should trigger proactive dialogue."""
        state = self.load_game_state()
        pet = state.get('pet', {})
        triggers = []
        
        # Pet health drop
        current_health = pet.get('health', 100)
        if current_health < 25 and self.last_pet_health >= 25:
            triggers.append({
                'text': f"Master! I am dying... {pet.get('name', 'I')} cannot hold much longer!",
                'priority': 'urgent',
                'color': 'red'
            })
        elif current_health < 50 and self.last_pet_health >= 50:
            triggers.append({
                'text': f"I am wounded, master. The battle takes its toll on me.",
                'priority': 'high',
                'color': 'orange'
            })
        self.last_pet_health = current_health
        
        # Pet death
        if pet.get('is_dead') and not getattr(self, 'pet_was_dead', False):
            triggers.append({
                'text': f"My essence fades... do not forget me, master...",
                'priority': 'urgent',
                'color': 'red'
            })
            self.pet_was_dead = True
        elif not pet.get('is_dead'):
            self.pet_was_dead = False
            
        # Zone change
        zone = state.get('zone', '')
        if zone and zone != self.last_zone:
            self.last_zone = zone
            triggers.append({
                'text': f"We arrive in {zone}. I sense the energy of this place.",
                'priority': 'low',
                'color': 'cyan'
            })
            
        # DBM timer (boss ability imminent)
        for timer in state.get('dbm_timers', []):
            timer_id = timer.get('id', '')
            time_remaining = timer.get('time_remaining', 999)
            if time_remaining < 5 and self.last_dbm_timers.get(timer_id, 999) >= 5:
                triggers.append({
                    'text': f"Danger! {timer.get('message', 'Unknown ability')} incoming!",
                    'priority': 'urgent',
                    'color': 'red'
                })
            self.last_dbm_timers[timer_id] = time_remaining
            
        # Player death
        # (Would need to track from combat log)
        
        return triggers
    
    def get_current_context_string(self):
        state = self.load_game_state()
        ctx_parts = []
        
        if 'player_name' in state:
            ctx_parts.append(f"Player: {state['player_name']} (Level {state.get('player_level', '?')})")
        if 'zone' in state:
            ctx_parts.append(f"Zone: {state['zone']}")
        if 'in_combat' in state:
            ctx_parts.append(f"Combat: {'Yes' if state['in_combat'] else 'No'}")
        if 'pet' in state and isinstance(state['pet'], dict):
            pet = state['pet']
            ctx_parts.append(f"Pet: {pet.get('name', '?')} ({pet.get('family', '?')}) - {pet.get('health', '?')}% HP")
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
