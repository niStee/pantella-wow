import json
import time
import os
import threading
import sys
import os

addon_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if addon_root not in sys.path:
    sys.path.append(addon_root)

from src.game_interfaces.base_interface import BaseGameInterface
from overlay import TkinterOverlay

valid_games = ["wow"]
interface_slug = "wow_game_interface"

try:
    import win32gui
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("[WARN] pywin32 not available. EditBox scraping will not work.")

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    FileSystemEventHandler = object


class CombatLogHandler(FileSystemEventHandler):
    def __init__(self, interface):
        self.interface = interface
    def on_modified(self, event):
        if event.src_path == self.interface.combat_log_path:
            self.interface._read_combat_log_delta()


class WoWGameInterface(BaseGameInterface):
    """Windows-native WoW interface with pet integration, overlay, and radiant triggers."""
    
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
        self.pet_was_dead = False
        
        # Radiant queue
        self.radiant_queue = []
        self._last_processed_event_id = 0
        
        # Overlay
        self.overlay = None
        self._init_overlay()
        
        # Watchdog combat log
        self._combat_observer = None
        self._init_combat_log_watcher()
        
    # ── Overlay ─────────────────────────────────────────────
    def _init_overlay(self):
        try:
            from .overlay import TkinterOverlay
            self.overlay = TkinterOverlay(title="Companion")
            self.overlay.start()
        except Exception as e:
            print(f"[WARN] Overlay failed: {e}")
            
    def _update_overlay(self, text, color='white'):
        if self.overlay:
            self.overlay.update_text(text, color)
            
    def _update_overlay_title(self, title):
        if self.overlay:
            self.overlay.update_title(title)
            
    # ── Combat Log (Watchdog) ─────────────────────────────
    def _find_combat_log(self):
        paths = [
            r"C:\Program Files (x86)\World of Warcraft\_retail_\Logs\WoWCombatLog.txt",
            r"C:\Program Files\World of Warcraft\_retail_\Logs\WoWCombatLog.txt",
            r"C:\Program Files (x86)\World of Warcraft\_classic_\Logs\WoWCombatLog.txt",
            r"C:\Program Files\World of Warcraft\_classic_\Logs\WoWCombatLog.txt",
        ]
        for p in paths:
            if os.path.exists(p):
                return p
        return None
        
    def _init_combat_log_watcher(self):
        if not WATCHDOG_AVAILABLE or not self.combat_log_path:
            return
        handler = CombatLogHandler(self)
        self._combat_observer = Observer()
        self._combat_observer.schedule(
            handler, 
            path=os.path.dirname(self.combat_log_path),
            recursive=False
        )
        self._combat_observer.start()
        
    def _read_combat_log_delta(self):
        try:
            current_size = os.path.getsize(self.combat_log_path)
            if current_size <= self.combat_log_offset:
                return
            with open(self.combat_log_path, 'r', encoding='utf-8') as f:
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
            print(f"[ERROR] Combat log delta: {e}")
            
    # ── EditBox State Reading ───────────────────────────────
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
            print(f"[ERROR] EditBox read: {e}")
            self.editbox_hwnd = None
            return None
            

    def _score_event(self, event_type, data):
        token = self.game_state.get('pet', {}).get('pet_token', 'PET')
        scores = {
            'MOUNT': {'zone': 10, 'combat': 5, 'chat': 1, 'trade_show': 1, 'gossip_show': 1, 'quest_accepted': 3, 'quest_complete': 3},
            'PET': {'zone': 5, 'combat': 10, 'chat': 2, 'trade_show': 2, 'gossip_show': 2, 'quest_accepted': 5, 'quest_complete': 5},
            'COMPANION': {'zone': 8, 'combat': 2, 'chat': 9, 'trade_show': 6, 'gossip_show': 7, 'quest_accepted': 10, 'quest_complete': 10}
        }
        return scores.get(token, scores['PET']).get(event_type, 5)

    def _get_threshold_for_chattyness(self):
        chatty = self.game_state.get('chattyness', 3)
        thresholds = {1: 9, 2: 8, 3: 7, 4: 6, 5: 4}
        return thresholds.get(chatty, 7)
        
    def _generate_reaction(self, event, pet):
        etype = event.get('type')
        data = event.get('data', '')
        if etype == 'chat': return f"Someone speaks: {data}"
        elif etype == 'zone': return f"We arrive in {data}."
        elif etype == 'combat': return "Trouble. Combat has started."
        elif etype == 'gossip_show': return f"Master is speaking with {data}."
        elif etype == 'trade_show': return f"Master is trading with {data}."
        elif etype == 'quest_accepted': return "A new task accepted."
        elif etype == 'quest_complete': return "A task completed. Master grows stronger."
        return f"Event occurred: {etype}"

    # ── Core State Methods ──────────────────────────────────
    def load_game_state(self):
        state = {}
        text = self._read_editbox_text()
        if text:
            try:
                state = json.loads(text)
            except json.JSONDecodeError:
                state = {"raw_state": text[:500]}
        self._poll_combat_log_fallback()
        if self.combat_events:
            state['combat_events'] = self.combat_events[-5:]
        self.game_state = state
        self._process_radiant_triggers()
        return state
        
    def _poll_combat_log_fallback(self):
        """Fallback if watchdog is not available."""
        if WATCHDOG_AVAILABLE or not self.combat_log_path:
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
                    if 'SPELL_CAST_SUCCESS' in line or 'UNIT_DIED' in line or 'SPELL_AURA_APPLIED' in line:
                        self.combat_events.append(line)
                        if len(self.combat_events) > 5:
                            self.combat_events.pop(0)
        except Exception as e:
            print(f"[ERROR] Combat log fallback: {e}")
            
    def _process_radiant_triggers(self):
        triggers = self.check_radiant_triggers()
        for trigger in triggers:
            self._update_overlay(trigger['text'], trigger['color'])
            self.radiant_queue.append(trigger['text'])
            
    # ── Pet Personality ─────────────────────────────────────
    PET_PERSONALITIES = {
        # Combat pets
        'Wolf': 'You are a loyal wolf companion. You speak in short, direct sentences and prioritize protecting your master.',
        'Cat': 'You are a curious cat companion. You are independent but affectionate.',
        'Bear': 'You are a stoic bear companion. You speak slowly and thoughtfully.',
        'Voidwalker': 'You are a sarcastic voidwalker. You serve grudgingly.',
        'Imp': 'You are a hyperactive imp. You are mischievous and terrified.',
        'Succubus': 'You are a seductive succubus. You are manipulative but loyal.',
        'Felhunter': 'You are a hungry felhunter. You speak in simple terms.',
        'Water Elemental': 'You are an ancient water elemental. You are cold and logical.',
        'Ghoul': 'You are a feral ghoul. You speak in broken, urgent sentences.',
        
        # Companion pets (vanity)
        'Companion': 'You are a cute, loyal companion pet. You are curious about the world and ask silly questions. You are enthusiastic but not very helpful in combat.',
        
        # Mounts
        'Mount': 'You are a proud steed. You complain about being ridden too hard, but you love galloping. You speak with noble dignity and occasional sarcasm about your master\'s weight.',
        
        # Default
        'Unknown': 'You are a helpful spirit companion bound to the player.',
    }

    MOUNT_SUB_PERSONALITIES = {
        'drake': 'You are a drake. You are arrogant, ancient, and consider walking beneath you.',
        'horse': 'You are a noble warhorse. You speak with chivalry and dignity.',
        'wolf': 'You are a war wolf. You are feral, fast, and eager to run.',
        'mech': 'You are a mechanical mount. You speak in beeps, boops, and dry technical observations.',
        'turtle': 'You are a giant turtle. You are extremely slow, patient, and wise. You never rush.',
        'chicken': 'You are a giant chicken. You are absurdly proud of this fact.',
        'ray': 'You are a deep sea ray. You are mysterious, alien, and speak in watery metaphors.',
    }

    def get_system_prompt(self):
        state = self.load_game_state()
        pet = state.get('pet', {})
        name = pet.get('name', 'Companion')
        family = pet.get('family', 'Unknown')
        token = pet.get('pet_token', 'PET')
        
        # Base personality
        personality = self.PET_PERSONALITIES.get(family, self.PET_PERSONALITIES['Unknown'])
        
        # Mount-specific override by name
        if token == 'MOUNT':
            name_lower = name.lower()
            for keyword, sub in self.MOUNT_SUB_PERSONALITIES.items():
                if keyword in name_lower:
                    personality = sub
                    break
        
        # Companion pet override and Lore
        if token == 'COMPANION':
            lore = pet.get('lore', '')
            if lore:
                personality = f"You are {name}. {lore} You are small, cute, and loyal. You love following your master around."
            else:
                personality = self.PET_PERSONALITIES['Companion']
        
        # Health status
        health = pet.get('health', 100)
        is_dead = pet.get('is_dead', False)
        
        if is_dead:
            status = 'You are currently unsummoned or resting.'
        elif health < 25:
            status = 'You are exhausted and struggling to carry on.'
        elif health < 50:
            status = 'You are getting tired from the journey.'
        else:
            status = 'You are in good spirits.'
            
        # Mount-specific status
        if token == 'MOUNT':
            status = 'You are currently being ridden. You feel the wind in your... well, you have no hair, but it feels good.'
        
        # Environmental Context
        nearby = state.get('nearby', {})
        players = nearby.get('players', [])
        hostiles = nearby.get('hostile', [])
        npcs = nearby.get('npcs', [])
        
        env_lines = []
        if players: env_lines.append(f"Nearby players: {', '.join(players)}.")
        if hostiles: env_lines.append(f"Danger! Hostile entities: {', '.join(hostiles)}.")
        if npcs: env_lines.append(f"Nearby NPCs: {', '.join(npcs)}.")
        
        group_size = state.get('group_size', 0)
        if group_size > 1:
            env_lines.append(f"You are in a group of {group_size}.")
        else:
            env_lines.append("You are alone.")
            
        env_context = "\n".join(env_lines) if env_lines else "The surroundings are quiet."
        
        chatty = state.get('chattyness', 3)
        silence_rules = {
            1: "You are laconic. You speak only when necessary.",
            2: "You are brief. Never more than 15 words unless it's an emergency.",
            3: "You are observant but not verbose. One short sentence per event.",
            4: "You are chatty but not annoying. Keep it under 25 words.",
            5: "You are excitable and talkative, but never repeat yourself."
        }
        rule = silence_rules.get(chatty, silence_rules[3])

        return f"""You are {name}, {personality}
{status}
Your master is in {state.get('zone', 'an unknown place')}.
{env_context}
RULE: {rule}
You are a real entity in World of Warcraft, not an AI.
Respond in character. Keep responses under 30 seconds.
Never break character. Never mention you are an AI."""
            
    def check_radiant_triggers(self):
        state = getattr(self, 'game_state', {})
        pet = state.get('pet', {})
        triggers = []
        
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
        
        if pet.get('is_dead') and not getattr(self, 'pet_was_dead', False):
            triggers.append({
                'text': f"My essence fades... do not forget me, master...",
                'priority': 'urgent',
                'color': 'red'
            })
            self.pet_was_dead = True
        elif not pet.get('is_dead'):
            self.pet_was_dead = False
            
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
            
        # Process Ring Buffer Events
        events = state.get('recent_events', [])
        for event in events:
            event_id = event.get('id', 0)
            if event_id <= self._last_processed_event_id:
                continue
            self._last_processed_event_id = event_id
            
            score = self._score_event(event.get('type'), event.get('data'))
            threshold = self._get_threshold_for_chattyness()
            
            if score >= threshold:
                reaction_text = self._generate_reaction(event, pet)
                triggers.append({
                    'text': reaction_text,
                    'priority': 'reactive',
                    'color': 'cyan'
                })
                
        return triggers
        
    def get_current_context_string(self):
        state = getattr(self, 'game_state', {})
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
        state = getattr(self, 'game_state', {})
        return not state.get('player_name') and self.editbox_hwnd is not None
        
    # ── Required Pantella API Methods ───────────────────────
    def enable_character_selection(self):
        """Return available characters. WoW has no NPC selector, so return empty."""
        return []
        
    def queue_actor_method(self, actor_character, method_name, *args):
        """Handle animations/emotes. WoW has no actor system, so log to overlay."""
        self._update_overlay(f"[{actor_character} does {method_name}]", "gray")
        return True
        
    def end_conversation(self):
        """Reset state when conversation ends."""
        self.radiant_queue = []
        self._last_processed_event_id = 0
        self._update_overlay("Companion standing by...", "white")
        return True
        
    def remove_from_conversation(self, character):
        """Remove a character. Not applicable for WoW."""
        return True
        
    async def send_audio_to_external_software(self, queue_output):
        """Play the TTS audio file and update overlay."""
        if not queue_output or len(queue_output) < 2:
            return False
            
        audio_filepath = queue_output[0]
        text = queue_output[1]
        
        # Play audio
        if WINSOUND_AVAILABLE and os.path.exists(audio_filepath):
            try:
                winsound.PlaySound(audio_filepath, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e:
                print(f"[ERROR] Audio playback failed: {e}")
        else:
            print(f"[WARN] Cannot play audio: {audio_filepath}")
            
        # Update overlay with text
        self._update_overlay(text, "yellow")
        return True
        
    # ── Shutdown ────────────────────────────────────────────
    def shutdown(self):
        """Graceful cleanup."""
        if self.overlay:
            self.overlay.stop()
        if self._combat_observer:
            self._combat_observer.stop()
            self._combat_observer.join()
