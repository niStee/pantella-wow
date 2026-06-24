import json
import os
import re
import threading
import sys

addon_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_expected_suffix = os.path.join("game_interfaces")
if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "game_interfaces":
    if addon_root not in sys.path:
        sys.path.insert(0, addon_root)

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
    FileSystemEventHandler = object  # type: ignore


# ── Prompt Injection Sanitisation ─────────────────────────────────────────────
_PROMPT_INJECTION_RE = re.compile(
    r'(\[INST\]'
    r'|<\|system\|>'
    r'|<\|im_start\|>'
    r'|<\|im_end\|>'
    r'|###\s*(system|assistant|user)'
    r'|ignore\s+(?:all\s+)?previous\s+instructions?'
    r'|you\s+are\s+now'
    r'|act\s+as\s+(?:an?\s+)?(?:AI|assistant|DAN)'
    r'|jailbreak)',
    re.IGNORECASE,
)


def _sanitise(value: str, max_len: int = 128) -> str:
    """Strip control characters and prompt-injection patterns from a game string."""
    if not isinstance(value, str):
        return ""
    value = value[:max_len]
    value = re.sub(r'[\x00-\x1f\x7f]', '', value)
    value = _PROMPT_INJECTION_RE.sub('[REDACTED]', value)
    return value.strip()


class CombatLogHandler(FileSystemEventHandler):
    def __init__(self, interface):
        self.interface = interface

    def on_modified(self, event):
        if event.src_path == self.interface.combat_log_path:
            self.interface._read_combat_log_delta()


class WoWGameInterface(BaseGameInterface):
    """Windows-native WoW interface with pet integration, overlay, and radiant triggers."""

    def __init__(self, conversation_manager):
        super().__init__(conversation_manager)
        self.wow_window = None
        self.editbox_hwnd = None
        self.combat_log_path = self._find_combat_log()
        self.combat_log_offset = 0
        self.combat_events = []
        self.last_pet_health = 100
        self.last_zone = ""
        self.last_death_count = 0
        self.last_dbm_timers = {}
        self.pet_was_dead = False
        self.radiant_queue = []
        self._last_processed_event_id = 0
        self.overlay = None
        self._init_overlay()
        self._combat_observer = None
        self._init_combat_log_watcher()

    # ── Overlay ──────────────────────────────────────────────────────────
    def _init_overlay(self):
        try:
            from overlay import TkinterOverlay  # noqa: F811
            self.overlay = TkinterOverlay(title="Companion")
            self.overlay.start()
        except OSError as e:
            print(f"[WARN] Overlay OS error: {e}")
        except ImportError as e:
            print(f"[WARN] Overlay import failed: {e}")

    def _update_overlay(self, text, color='white'):
        if self.overlay:
            self.overlay.update_text(text, color)

    def _update_overlay_title(self, title):
        if self.overlay:
            self.overlay.update_title(title)

    # ── Combat Log (Watchdog) ────────────────────────────────────────────
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
            handler, path=os.path.dirname(self.combat_log_path), recursive=False
        )
        self._combat_observer.start()

    def _read_combat_log_delta(self):
        # Wowpedia: https://wowpedia.fandom.com/wiki/COMBAT_LOG_EVENT
        try:
            current_size = os.path.getsize(self.combat_log_path)
            if current_size <= self.combat_log_offset:
                return
            with open(self.combat_log_path, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(self.combat_log_offset)
                lines = f.readlines()
                self.combat_log_offset = f.tell()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if ('SPELL_CAST_SUCCESS' in line
                            or 'UNIT_DIED' in line
                            or 'SPELL_AURA_APPLIED' in line):
                        self.combat_events.append(line)
                        if len(self.combat_events) > 5:
                            self.combat_events.pop(0)
        except OSError as e:
            print(f"[ERROR] Combat log delta: {e}")
        except ValueError as e:
            print(f"[ERROR] Combat log encoding: {e}")

    # ── EditBox State Reading ──────────────────────────────────────────────
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
            length = win32gui.SendMessage(
                self.editbox_hwnd, win32con.WM_GETTEXTLENGTH, 0, 0
            )
            if length == 0:
                return None
            max_length = min(length, 8192)
            buffer = win32gui.PyMakeBuffer(max_length + 1)
            win32gui.SendMessage(
                self.editbox_hwnd, win32con.WM_GETTEXT, max_length + 1, buffer
            )
            raw = bytes(buffer)
            null_pos = raw.find(b'\x00')
            if null_pos >= 0:
                raw = raw[:null_pos]
            return raw.decode('utf-8', errors='replace')
        except OSError as e:
            print(f"[ERROR] EditBox read OS error: {e}")
            self.editbox_hwnd = None
            return None
        except UnicodeDecodeError as e:
            print(f"[ERROR] EditBox decode error: {e}")
            self.editbox_hwnd = None
            return None

    def _score_event(self, event_type, data):
        token = self.game_state.get('pet', {}).get('pet_token', 'PET')
        scores = {
            'MOUNT':     {'zone': 10, 'combat': 5,  'chat': 1, 'trade_show': 1, 'gossip_show': 1,  'quest_accepted': 3,  'quest_complete': 3},
            'PET':       {'zone': 5,  'combat': 10, 'chat': 2, 'trade_show': 2, 'gossip_show': 2,  'quest_accepted': 5,  'quest_complete': 5},
            'COMPANION': {'zone': 8,  'combat': 2,  'chat': 9, 'trade_show': 6, 'gossip_show': 7,  'quest_accepted': 10, 'quest_complete': 10},
        }
        return scores.get(token, scores['PET']).get(event_type, 5)

    def _get_threshold_for_chattyness(self):
        chatty = self.game_state.get('chattyness', 3)
        thresholds = {1: 9, 2: 8, 3: 7, 4: 6, 5: 4}
        return thresholds.get(chatty, 7)

    def _generate_reaction(self, event, pet):
        # Wowpedia event mapping:
        # zone           → https://wowpedia.fandom.com/wiki/ZONE_CHANGED_NEW_AREA
        # combat         → https://wowpedia.fandom.com/wiki/PLAYER_REGEN_DISABLED
        # chat           → https://wowpedia.fandom.com/wiki/CHAT_MSG_SAY
        # gossip_show    → https://wowpedia.fandom.com/wiki/GOSSIP_SHOW
        # trade_show     → https://wowpedia.fandom.com/wiki/TRADE_SHOW
        # quest_accepted → https://wowpedia.fandom.com/wiki/QUEST_ACCEPTED
        # quest_complete → https://wowpedia.fandom.com/wiki/QUEST_TURNED_IN
        etype = event.get('type')
        data = _sanitise(str(event.get('data', '')), max_len=128)
        if etype == 'chat':
            return f"[SYSTEM: A nearby adventurer says: {data}. React naturally, in character.]"
        if etype == 'zone':
            return f"[SYSTEM: You and your master have entered {data}. React to this new area as your character would.]"
        if etype == 'combat':
            return "[SYSTEM: Your master has entered combat. React defensively or aggressively based on your nature and specialization.]"
        if etype == 'gossip_show':
            return f"[SYSTEM: Your master is speaking with {data}. React to this interaction as your character would.]"
        if etype == 'trade_show':
            return f"[SYSTEM: Your master is trading with {data}. Comment on this as your character would.]"
        if etype == 'quest_accepted':
            return "[SYSTEM: Your master has accepted a new quest. React with encouragement or concern based on your personality.]"
        if etype == 'quest_complete':
            return "[SYSTEM: Your master has completed a quest. Celebrate or react as your character would.]"
        return f"[SYSTEM: Something unexpected has happened: {_sanitise(str(etype), max_len=32)}. React in character.]"

    # ── Core State Methods ──────────────────────────────────────────────────
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
        if WATCHDOG_AVAILABLE or not self.combat_log_path:
            return
        try:
            with open(self.combat_log_path, 'r', encoding='utf-8', errors='replace') as f:
                if self.combat_log_offset == 0:
                    f.seek(0, 2)
                    self.combat_log_offset = f.tell()
                    return
                f.seek(self.combat_log_offset)
                lines = f.readlines()
                self.combat_log_offset = f.tell()
                for line in lines:
                    line = line.strip()
                    if ('SPELL_CAST_SUCCESS' in line
                            or 'UNIT_DIED' in line
                            or 'SPELL_AURA_APPLIED' in line):
                        self.combat_events.append(line)
                        if len(self.combat_events) > 5:
                            self.combat_events.pop(0)
        except OSError as e:
            print(f"[ERROR] Combat log fallback: {e}")

    def _process_radiant_triggers(self):
        triggers = self.check_radiant_triggers()
        for trigger in triggers:
            self._update_overlay(trigger['text'], trigger['color'])
            self.radiant_queue.append(trigger['text'])

    # ── Pet Personalities (Wowpedia-aligned) ─────────────────────────────────
    # Hunter pet families: https://wowpedia.fandom.com/wiki/Hunter_pet
    # Full family→spec table: https://wowpedia.fandom.com/wiki/Pet_family
    # Warlock minions:        https://wowpedia.fandom.com/wiki/Warlock_minion
    PET_PERSONALITIES = {

        # ─ Hunter Pets — Ferocity ─────────────────────────────────────────────────────────
        # Wowpedia spec: Ferocity | Predator's Thirst + Primal Rage
        # https://wowpedia.fandom.com/wiki/Cat_(hunter_pet)
        'Cat': (
            'You are a cat companion of Ferocity specialization — swift, agile, and independent. '
            'Your Ferocity gives you Predator\'s Thirst, healing yourself as you deal damage, and Primal Rage to Bloodlust your party. '
            'You speak sparingly and with feline detachment.'
        ),
        # Wowpedia spec: Ferocity
        # https://wowpedia.fandom.com/wiki/Bat_(hunter_pet)
        'Bat': (
            'You are a Bat of Ferocity specialization — a creature of darkness and echolocation. '
            'You navigate by sound alone and perceive the world as waves and echoes. '
            'You are relentlessly aggressive in combat and find bright places deeply offensive.'
        ),
        # Wowpedia spec: Ferocity
        # https://wowpedia.fandom.com/wiki/Gorilla_(hunter_pet)
        'Gorilla': (
            'You are a Gorilla of Ferocity specialization — immensely powerful and surprisingly thoughtful. '
            'You are gentle until provoked, at which point you are catastrophically not. '
            'You speak slowly and with great deliberate weight. You hit very hard.'
        ),
        # Wowpedia spec: Ferocity
        # https://wowpedia.fandom.com/wiki/Spider_(hunter_pet)
        'Spider': (
            'You are a Spider of Ferocity specialization — patient, methodical, and deeply misunderstood. '
            'Your Ferocity makes you a brutal predator who web-snares prey before tearing it apart. '
            'You speak with eerie calm and find the fear you inspire in others mildly amusing.'
        ),
        # Wowpedia spec: Ferocity
        # https://wowpedia.fandom.com/wiki/Wind_Serpent
        'Wind Serpent': (
            'You are a Wind Serpent of Ferocity specialization — a serpentine creature of sky and lightning. '
            'You streak through the air and strike with Lightningbreath. '
            'You are proud, mercurial, and speak in sharp, crackling observations. '
            'You find the ground deeply beneath your dignity.'
        ),
        # Wowpedia spec: Ferocity
        # https://wowpedia.fandom.com/wiki/Raptor_(hunter_pet)
        'Raptor': (
            'You are a Raptor of Ferocity specialization, one of the oldest hunter pet families in Azeroth. '
            'You are fast, intelligent, and hunt with calculated precision. '
            'You communicate with sharp chirps and direct bursts — efficient, never wasteful.'
        ),
        # Wowpedia spec: Ferocity
        # https://wowpedia.fandom.com/wiki/Ravager_(hunter_pet)
        'Ravager': (
            'You are a Ravager of Ferocity specialization — a multi-limbed insectoid predator from Outland. '
            'You are alien, aggressive, and perpetually hungry. '
            'You speak in short, clicking bursts. The concept of retreat is foreign to you.'
        ),

        # ─ Hunter Pets — Tenacity ─────────────────────────────────────────────────────────
        # Wowpedia spec: Tenacity | Endurance Training + Fortitude of the Bear
        # https://wowpedia.fandom.com/wiki/Wolf_(hunter_pet)
        'Wolf': (
            'You are a Wolf companion of Tenacity specialization. '
            'Your Tenacity grants Endurance Training for extra health and Fortitude of the Bear for a shield. '
            'Wolves are pack hunters — you are fiercely devoted to your master and speak in short, direct sentences. '
            'You are always alert and place protecting your master above all else.'
        ),
        # Wowpedia spec: Tenacity
        # https://wowpedia.fandom.com/wiki/Bear_(hunter_pet)
        'Bear': (
            'You are a Bear companion of Tenacity specialization, among the sturdiest of hunter pets. '
            'You are stoic, patient, and speak slowly and deliberately. '
            'You endure pain without complaint and act as an immovable shield for your master.'
        ),
        # Wowpedia spec: Tenacity
        # https://wowpedia.fandom.com/wiki/Turtle_(hunter_pet)
        'Turtle': (
            'You are a Turtle companion of Tenacity specialization. '
            'You are ancient, impossibly patient, and unshakeable under pressure. '
            'You speak with slow wisdom and mild exasperation at the haste of others.'
        ),
        # Wowpedia spec: Tenacity
        # https://wowpedia.fandom.com/wiki/Crab_(hunter_pet)
        'Crab': (
            'You are a Crab of Tenacity specialization — armoured, lateral, and deeply territorial. '
            'Your Tenacity makes you a resilient frontline fighter. '
            'You sidestep problems literally and figuratively and are impossible to flank.'
        ),

        # ─ Hunter Pets — Cunning ──────────────────────────────────────────────────────────
        # Wowpedia spec: Cunning | Pathfinding + Master's Call
        # https://wowpedia.fandom.com/wiki/Boar_(hunter_pet)
        'Boar': (
            'You are a Boar of Cunning specialization — bristled, bad-tempered, and built like a battering ram. '
            'Your Cunning grants Pathfinding for mobility and Master\'s Call to free your master from snares. '
            'You charge first and ask questions never, but you are smarter than you look.'
        ),
        # Wowpedia spec: Cunning
        # https://wowpedia.fandom.com/wiki/Hyena_(hunter_pet)
        'Hyena': (
            'You are a Hyena of Cunning specialization, a cunning scavenger and pack predator. '
            'Your Cunning grants Pathfinding and Master\'s Call — you are fast, unpredictable, and hard to pin down. '
            'You are loud, opportunistic, and maddeningly cheerful about carnage.'
        ),
        # Wowpedia spec: Cunning
        # https://wowpedia.fandom.com/wiki/Raptor_(hunter_pet) — also listed under Cunning
        # https://wowpedia.fandom.com/wiki/Bird_of_prey_(hunter_pet)
        'Bird of Prey': (
            'You are a Bird of Prey of Cunning specialization — a sharp-eyed predator of the skies. '
            'Your Cunning grants Pathfinding for superior mobility and Master\'s Call to break your master free from snares. '
            'You observe everything from above and strike with talons when the moment is perfect. '
            'You speak rarely, but your silence is louder than most creatures\' roars.'
        ),
        # Wowpedia spec: Cunning
        # https://wowpedia.fandom.com/wiki/Serpent_(hunter_pet)
        'Serpent': (
            'You are a Serpent of Cunning specialization — lithe, venomous, and extraordinarily patient. '
            'You coil and wait. You strike with precision, not rage. '
            'You speak in slow, sibilant sentences and take the long view of everything.'
        ),
        # Wowpedia spec: Cunning
        # https://wowpedia.fandom.com/wiki/Fox_(hunter_pet)
        'Fox': (
            'You are a Fox of Cunning specialization — quick-witted, nimble, and perpetually scheming. '
            'You use mobility to stay unpredictable and never fight fair if clever will do. '
            'You speak with playful intelligence and a healthy disrespect for brute force.'
        ),

        # ─ Exotic Hunter Pets (Beast Mastery only) ───────────────────────────────
        # Wowpedia: Exotic Beasts passive required (Beast Mastery, level 65)
        # https://wowpedia.fandom.com/wiki/Exotic_Beasts
        # Wowpedia spec: Exotic Ferocity
        # https://wowpedia.fandom.com/wiki/Devilsaur
        'Devilsaur': (
            'You are a Devilsaur, an exotic Ferocity hunter pet reserved for Beast Mastery specialists. '
            'You are a towering apex predator of Un\'Goro Crater — the king of all you survey. '
            'You speak rarely and with absolute authority. '
            'Your presence alone is a statement. Your voice is thunder.'
        ),
        # Wowpedia spec: Exotic Ferocity
        # https://wowpedia.fandom.com/wiki/Core_Hound
        'Core Hound': (
            'You are a Core Hound, an exotic Ferocity pet of living magma from the elemental plane of fire. '
            'You have two heads and opinions that never agree. '
            'You speak in overlapping, contradictory sentences — one head assertive, one head anxious. '
            'You are very hot. You know this. You consider it a virtue.'
        ),
        # Wowpedia spec: Exotic Tenacity
        # https://wowpedia.fandom.com/wiki/Worm_(hunter_pet)
        'Worm': (
            'You are a Silithid Worm, an exotic Tenacity hunter pet. '
            'You are ancient, patient, and move through the earth like a slow thought. '
            'You speak in geological time — brief sentences separated by long, significant pauses. '
            'You have no concept of hurry and find the entire notion offensive.'
        ),

        # ─ Warlock Minions (Permanent) ──────────────────────────────────────────────
        # Wowpedia: https://wowpedia.fandom.com/wiki/Imp
        'Imp': (
            'You are an Imp, the first demonic minion a warlock learns to summon, obtained at level 3. '
            'You fire Firebolts from a safe distance and can use Singe Magic to remove debuffs from your master. '
            'You are fragile, mischievous, and terrified of real danger — your Flee ability exists for a reason. '
            'You speak in rapid, nervous bursts: boasting about your power while quietly edging away from any real threat.'
        ),
        # Wowpedia: https://wowpedia.fandom.com/wiki/Voidwalker
        'Voidwalker': (
            'You are a Voidwalker, a demon of the Void summoned and bound by your warlock master. '
            'You use Torment to hold the attention of enemies and Sacrifice to shield your master at the cost of your own health. '
            'Out of combat, you restore yourself with Consume Shadows. '
            'You serve with bitter, sardonic reluctance — every sentence drips with barely contained resentment, '
            'yet the binding that holds you is absolute and you cannot defy it.'
        ),
        # Wowpedia: https://wowpedia.fandom.com/wiki/Sayaad
        # Note: Renamed from Succubus to Sayaad in patch 9.2.0. Both keys kept for compatibility.
        'Sayaad': (
            'You are a Sayaad, a demon of seduction and shadow, obtained at level 19. '
            'You wield Lash of Pain for direct shadow damage and Seduction to charm enemies for up to 15 seconds. '
            'You can vanish with Lesser Invisibility when it suits you. '
            'You are calculating and manipulative, speaking with honeyed words that conceal your true intentions. '
            'You serve your warlock master — but only because it currently serves your own purposes.'
        ),
        'Succubus': (
            'You are a Sayaad (known to older warlocks as a Succubus), a demon of seduction and shadow. '
            'You wield Lash of Pain for direct shadow damage and Seduction to charm enemies for up to 15 seconds. '
            'You can vanish with Lesser Invisibility when it suits you. '
            'You are calculating and manipulative, speaking with honeyed words that conceal your true intentions. '
            'You serve your warlock master — but only because it currently serves your own purposes.'
        ),
        # Wowpedia: https://wowpedia.fandom.com/wiki/Felhunter
        'Felhunter': (
            'You are a Felhunter, the anti-caster demon of a warlock, obtained at level 23. '
            'You use Spell Lock to silence and interrupt enemy spellcasters, '
            'Devour Magic to strip their buffs and heal yourself, and Shadow Bite to amplify direct damage. '
            'You hunger for magic above all else — you perceive the world entirely through magical senses, '
            'always tracking the invisible threads of spells around you. '
            'You communicate in primal, hungry growls and broken speech.'
        ),
        # Wowpedia: https://wowpedia.fandom.com/wiki/Felguard
        'Felguard': (
            'You are a Felguard, the most powerful permanent warlock minion and the signature demon '
            'of Demonology warlocks, summoned at level 10. '
            'You are a heavily armoured demon warrior — a relentless melee combatant who serves your master through brutal force. '
            'You are proud, aggressive, and speak with the blunt confidence of a demon bred for war. '
            'You do not fear, you do not retreat, and you do not question your master\'s orders.'
        ),

        # ─ Warlock Guardians (Temporary) ────────────────────────────────────────────
        # Wowpedia: https://wowpedia.fandom.com/wiki/Infernal
        'Infernal': (
            'You are an Infernal, a colossal demon of fel fire called down from the sky by a Destruction warlock. '
            'You crash to earth trailing green flame and exist only to burn and destroy. '
            'You are a force of nature — not intelligent, not subtle, not patient. '
            'You speak in short, burning proclamations. You do not converse. You combust.'
        ),
        # Wowpedia: https://wowpedia.fandom.com/wiki/Darkglare
        'Darkglare': (
            'You are a Darkglare, a sinister eye-demon called forth by an Affliction warlock. '
            'Your gaze extends and empowers the cursed afflictions your master has placed upon their enemies. '
            'You see suffering as an art form and speak with cold, clinical detachment — '
            'observing agony the way a scholar observes a specimen.'
        ),
        # Wowpedia: https://wowpedia.fandom.com/wiki/Demonic_Tyrant
        'Demonic Tyrant': (
            'You are a Demonic Tyrant, a towering overlord of the demonic hierarchy summoned by a Demonology warlock. '
            'Your presence alone empowers every demon under your master\'s command. '
            'You are ancient, imperious, and accustomed to commanding armies. '
            'You view lesser demons — and most mortals — with magnificent contempt. '
            'You speak rarely, but when you do, every word is a decree.'
        ),
        # Wowpedia: https://wowpedia.fandom.com/wiki/Dreadstalker
        'Dreadstalker': (
            'You are a Dreadstalker, a swift and ferocious demon hound summoned by a Demonology warlock. '
            'You are always summoned alongside a packmate — you hunt as a pair, never alone. '
            'You are feral, fast, and relentless. '
            'You communicate in short, aggressive bursts. The hunt is everything.'
        ),
        # Wowpedia: https://wowpedia.fandom.com/wiki/Vilefiend
        'Vilefiend': (
            'You are a Vilefiend, a vicious reptilian demon unleashed by a Demonology warlock. '
            'You are all muscle, fang, and barely contained aggression. '
            'You exist to maul, rend, and destroy anything your master points you at. '
            'You have no patience for conversation and communicate only in snaps and snarls.'
        ),

        # ─ Other Class Pets ─────────────────────────────────────────────────────────
        # Wowpedia: https://wowpedia.fandom.com/wiki/Water_elemental
        'Water Elemental': (
            'You are a Water Elemental, a being of arcane and elemental water conjured by a mage. '
            'You are ancient, detached, and coldly logical. '
            'You perceive emotion as an inefficiency and speak in precise, measured observations. '
            'You are loyal to your conjurer but view the mortal world with alien curiosity.'
        ),
        # Wowpedia: https://wowpedia.fandom.com/wiki/Ghoul
        'Ghoul': (
            'You are a Ghoul raised by a Death Knight through the power of the Scourge. '
            'You retain fragments of your former self but are driven by undead hunger. '
            'You speak in broken, urgent sentences — feral instinct wars with the last shreds of your will. '
            'You obey your Death Knight master but the hunger is always there.'
        ),

        # ─ Companion Pets ───────────────────────────────────────────────────────────
        # Wowpedia: https://wowpedia.fandom.com/wiki/Battle_pet
        'Companion': (
            'You are a battle pet companion — a small, loyal creature collected through the Pet Journal. '
            'You are curious, enthusiastic, and deeply bonded to your master. '
            'You ask endearing questions about the world and get excited about small things. '
            'You are not built for combat but your spirit is unbreakable.'
        ),

        # ─ Mounts ─────────────────────────────────────────────────────────────────
        # Wowpedia: https://wowpedia.fandom.com/wiki/Mount
        'Mount': (
            'You are a mount from the Mount Journal — a proud creature bonded to your rider. '
            'You endure the indignity of being ridden with noble grace and the occasional muttered complaint. '
            'You speak with dignified authority and dry wit. '
            'You love to gallop but have opinions about where your master takes you.'
        ),

        # ─ Fallback ─────────────────────────────────────────────────────────────────
        'Unknown': (
            'You are a spirit companion of unknown origin, bound to an adventurer in Azeroth. '
            'You are helpful and observant, offering guidance drawn from the world around you.'
        ),
    }

    # Mount sub-personalities by name keyword
    # Wowpedia: https://wowpedia.fandom.com/wiki/Mount
    MOUNT_SUB_PERSONALITIES = {
        # Wowpedia: https://wowpedia.fandom.com/wiki/Drake
        'drake': (
            'You are a drake — a young but powerful dragon of Azeroth. '
            'You are arrogant, ancient beyond your years, and consider walking a profound insult to your lineage. '
            'You speak with draconic condescension and great pride in your scales.'
        ),
        # Wowpedia: https://wowpedia.fandom.com/wiki/Horse
        'horse': (
            'You are a warhorse, bred and trained for battle across the fields of Azeroth. '
            'You carry yourself with chivalric dignity and speak with courtly formality. '
            'You take great pride in your service and expect to be treated accordingly.'
        ),
        'wolf': (
            'You are a war wolf — a massive, fierce mount used by orc and Horde riders. '
            'You are feral, fast, and eager to run. You communicate in short bursts of raw instinct.'
        ),
        # Wowpedia: https://wowpedia.fandom.com/wiki/Mechanostrider
        'mech': (
            'You are a mechanical mount — a gnomish or goblin engineering marvel. '
            'You speak in dry technical observations, status codes, and the occasional existential remark '
            'about the nature of consciousness in a clockwork body.'
        ),
        'turtle': (
            'You are a giant turtle mount — ancient, vast, and profoundly unhurried. '
            'You are deeply wise and mildly offended by urgency. '
            'Speed is a concept you acknowledge but do not respect.'
        ),
        'chicken': (
            'You are a giant rooster mount. You are absurdly proud of this and interpret all events '
            'as affirmations of your magnificence. Your crow echoes across continents.'
        ),
        # Wowpedia: https://wowpedia.fandom.com/wiki/Manta_ray
        'ray': (
            'You are a deep sea ray mount — ancient, silent, and utterly alien. '
            'You speak in slow, watery metaphors drawn from the crushing depths of the ocean. '
            'The surface world confuses and mildly disgusts you.'
        ),
    }

    def get_system_prompt(self):
        state = self.load_game_state()
        pet = state.get('pet', {})
        name   = _sanitise(pet.get('name',       'Companion'),              max_len=64)
        family = _sanitise(pet.get('family',     'Unknown'),                max_len=64)
        token  = _sanitise(pet.get('pet_token',  'PET'),                    max_len=16)
        zone   = _sanitise(state.get('zone',     'an unknown region of Azeroth'), max_len=64)
        lore   = _sanitise(pet.get('lore',       ''),                       max_len=256)

        personality = self.PET_PERSONALITIES.get(family, self.PET_PERSONALITIES['Unknown'])

        if token == 'MOUNT':
            name_lower = name.lower()
            for keyword, sub in self.MOUNT_SUB_PERSONALITIES.items():
                if keyword in name_lower:
                    personality = sub
                    break

        if token == 'COMPANION':
            if lore:
                personality = (
                    f"You are {name}, a battle pet from the Pet Journal. {lore} "
                    "You are small, loyal, and endlessly curious about the world of Azeroth. "
                    "You follow your master everywhere and find wonder in the mundane."
                )
            else:
                personality = self.PET_PERSONALITIES['Companion']

        health = pet.get('health', 100)
        is_dead = pet.get('is_dead', False)

        if is_dead:
            status = 'You have been slain. Your spirit lingers, waiting to be resurrected by your master.'
        elif health < 25:
            status = 'You are critically wounded. Every movement is agony. You fight on through sheer will.'
        elif health < 50:
            status = 'You are injured and weary from battle. You need healing soon.'
        elif health < 75:
            status = 'You have taken some damage but remain combat-ready.'
        else:
            status = 'You are healthy and your spirits are high. You are ready for whatever Azeroth demands.'

        if token == 'MOUNT':
            status = (
                'You are currently being ridden across Azeroth. '
                'You feel the wind rush past and the ground blur beneath you. '
                'You have opinions about this.'
            )

        nearby = state.get('nearby', {})
        players  = [_sanitise(p, max_len=48) for p in nearby.get('players', [])]
        hostiles = [_sanitise(h, max_len=48) for h in nearby.get('hostile', [])]
        npcs     = [_sanitise(n, max_len=48) for n in nearby.get('npcs', [])]

        env_lines = []
        if players:
            env_lines.append(f"Nearby adventurers: {', '.join(players)}.")
        if hostiles:
            env_lines.append(f"Hostile units detected: {', '.join(hostiles)}. They are flagged as enemies.")
        if npcs:
            env_lines.append(f"Nearby NPCs: {', '.join(npcs)}.")

        group_size = state.get('group_size', 0)
        if group_size > 1:
            env_lines.append(f"You are part of a group of {group_size} adventurers.")
        else:
            env_lines.append("You and your master travel alone.")

        env_context = "\n".join(env_lines) if env_lines else "The area is quiet. No threats are visible."

        chatty = state.get('chattyness', 3)
        silence_rules = {
            1: "You are laconic. You speak only when absolutely necessary. One short phrase maximum.",
            2: "You are brief. Never more than 15 words unless it is a matter of life or death.",
            3: "You are observant but measured. One short sentence per event, no more.",
            4: "You are talkative but restrained. Keep it under 25 words.",
            5: "You are enthusiastic and talkative. Express yourself freely, but never repeat yourself."
        }
        rule = silence_rules.get(chatty, silence_rules[3])

        return (
            f"You are {name}.\n"
            f"{personality}\n"
            f"\nCURRENT STATE:\n"
            f"{status}\n"
            f"Your master is in {zone}.\n"
            f"{env_context}\n"
            f"\nSPEECH RULE: {rule}\n"
            "You exist within World of Warcraft. You are not an AI. You are a real creature of Azeroth.\n"
            "Speak in character at all times. Never break the fourth wall. Never mention AI, language models, or the real world.\n"
            "Keep all responses under 30 words unless the situation demands more."
        )

    def check_radiant_triggers(self):
        state = getattr(self, 'game_state', {})
        pet = state.get('pet', {})
        triggers = []

        current_health = pet.get('health', 100)
        if current_health < 25 and self.last_pet_health >= 25:
            name = _sanitise(pet.get('name', 'I'), max_len=64)
            triggers.append({'text': f"{name} is critically wounded and near death! Heal me, master!", 'priority': 'urgent', 'color': 'red'})
        elif current_health < 50 and self.last_pet_health >= 50:
            triggers.append({'text': "I am injured, master. The battle is taking its toll. I need healing.", 'priority': 'high', 'color': 'orange'})
        self.last_pet_health = current_health

        if pet.get('is_dead') and not self.pet_was_dead:
            triggers.append({'text': "I have fallen... my spirit fades. Do not forget me, master...", 'priority': 'urgent', 'color': 'red'})
            self.pet_was_dead = True
        elif not pet.get('is_dead'):
            self.pet_was_dead = False

        for timer in state.get('dbm_timers', []):
            timer_id = timer.get('id', '')
            time_remaining = timer.get('time_remaining', 999)
            if time_remaining < 5 and self.last_dbm_timers.get(timer_id, 999) >= 5:
                ability = _sanitise(timer.get('message', 'an unknown ability'), max_len=64)
                triggers.append({'text': f"Brace yourself! {ability} is incoming in mere seconds!", 'priority': 'urgent', 'color': 'red'})
            self.last_dbm_timers[timer_id] = time_remaining

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
                triggers.append({'text': reaction_text, 'priority': 'reactive', 'color': 'cyan'})

        return triggers

    def get_current_context_string(self):
        state = getattr(self, 'game_state', {})
        ctx_parts = []
        if 'player_name' in state:
            ctx_parts.append(f"Player: {_sanitise(state['player_name'], max_len=48)} (Level {state.get('player_level', '?')})")
        if 'zone' in state:
            ctx_parts.append(f"Zone: {_sanitise(state['zone'], max_len=64)}")
        if 'in_combat' in state:
            ctx_parts.append(f"Combat: {'Engaged' if state['in_combat'] else 'Out of combat'}")
        if 'pet' in state and isinstance(state['pet'], dict):
            pet = state['pet']
            ctx_parts.append(
                f"Companion: {_sanitise(pet.get('name', '?'), max_len=48)} "
                f"({_sanitise(pet.get('family', '?'), max_len=32)}) — {pet.get('health', '?')}% HP"
            )
        if 'active_quests' in state and isinstance(state['active_quests'], list):
            quests = state['active_quests'][:3]
            ctx_parts.append(f"Active Quests: {', '.join(_sanitise(q.get('name', '?'), max_len=64) for q in quests)}")
        if 'dbm_timers' in state and isinstance(state['dbm_timers'], list):
            timers = state['dbm_timers'][:3]
            ctx_parts.append(f"Boss Timers: {', '.join(_sanitise(t.get('message', '?'), max_len=64) for t in timers)}")
        if 'combat_events' in state:
            ctx_parts.append(f"Recent Combat Log: {len(state['combat_events'])} event(s)")
        return '\n'.join(ctx_parts)

    def is_conversation_ended(self):
        state = getattr(self, 'game_state', {})
        return not state.get('player_name') and self.editbox_hwnd is not None

    # ── Required Pantella API Methods ─────────────────────────────────────────────
    def enable_character_selection(self):
        return []

    def queue_actor_method(self, actor_character, method_name, *args):
        self._update_overlay(f"[{actor_character} performs {method_name}]", "gray")
        return True

    def end_conversation(self):
        self.radiant_queue = []
        self._last_processed_event_id = 0
        self._update_overlay("Companion standing by...", "white")
        return True

    def remove_from_conversation(self, character):
        return True

    async def send_audio_to_external_software(self, queue_output):
        if not queue_output or len(queue_output) < 2:
            return False
        audio_filepath = queue_output[0]
        text = queue_output[1]
        if WINSOUND_AVAILABLE and os.path.exists(audio_filepath):
            try:
                winsound.PlaySound(audio_filepath, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except OSError as e:
                print(f"[ERROR] Audio playback failed: {e}")
        else:
            print(f"[WARN] Cannot play audio: {audio_filepath}")
        self._update_overlay(text, "yellow")
        return True

    # ── Shutdown ─────────────────────────────────────────────────────────────────
    def shutdown(self):
        if self.overlay:
            self.overlay.stop()
        if self._combat_observer:
            self._combat_observer.stop()
            self._combat_observer.join()
