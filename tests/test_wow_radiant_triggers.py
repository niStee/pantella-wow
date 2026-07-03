"""
TDD: WoWGameInterface Radiant Trigger Tests

Tests cover:
  1. Health threshold triggers (100→25, 100→49, 50→24)
  2. No duplicate trigger when health stays below threshold
  3. Death trigger fires once, not again while still dead
  4. Resurrection resets death flag (trigger fires again on next death)
  5. DBM timer trigger fires when time_remaining drops below 5
     ⚠️  SKIPPED — DBM schema not yet implemented in Lua addon.
         See: https://github.com/niStee/pantella-wow/issues (DBM Schema issue)
         Real schema uses DBM:RegisterCallback("DBM_TimerUpdate", fn(timer, elapsed, total))
         Source: https://github.com/WeakAuras/WeakAuras2 (DBM trigger integration)
  6. Radiant event reactions — score >= threshold fires trigger
  7. Radiant event reactions — score < threshold does not fire
  8. Already-processed event IDs are skipped
  9. Multiple events in one poll — only qualifying ones fire
  10. Triggers accumulate in radiant_queue via _process_radiant_triggers
  11. end_conversation resets radiant_queue

Wowpedia API references (verified stable):
  UnitHealth          → https://wowpedia.fandom.com/wiki/UnitHealth
  UnitIsDeadOrGhost   → https://wowpedia.fandom.com/wiki/UnitIsDeadOrGhost
  ZONE_CHANGED_NEW_AREA → https://wowpedia.fandom.com/wiki/ZONE_CHANGED_NEW_AREA
  PLAYER_REGEN_DISABLED → https://wowpedia.fandom.com/wiki/PLAYER_REGEN_DISABLED

DBM callback reference (NOT Wowpedia — external addon API):
  DBM_TimerUpdate → https://github.com/WeakAuras/WeakAuras2 (DBM trigger source)
  Real schema: timer object, elapsed (number), total (number)
  Our current schema {id, time_remaining, message} is a placeholder — NOT implemented in Lua addon yet.
"""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# ── Stub platform dependencies ──────────────────────────────────────────────
for mod in ['win32gui', 'win32con', 'winsound', 'watchdog',
            'watchdog.observers', 'watchdog.events']:
    sys.modules.setdefault(mod, MagicMock())

_base_mod = types.ModuleType('src.game_interfaces.base_interface')
_base_mod.BaseGameInterface = object
sys.modules['src'] = types.ModuleType('src')
sys.modules['src.game_interfaces'] = types.ModuleType('src.game_interfaces')
sys.modules['src.game_interfaces.base_interface'] = _base_mod
_overlay_mod = types.ModuleType('overlay')
_overlay_mod.TkinterOverlay = MagicMock
sys.modules['overlay'] = _overlay_mod

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from game_interfaces.wow import WoWGameInterface  # noqa: E402


# ── Shared fixture ───────────────────────────────────────────────────────────
def make_interface():
    iface = WoWGameInterface.__new__(WoWGameInterface)
    iface.overlay = None
    iface.editbox_hwnd = None
    iface.wow_window = None
    iface.combat_log_path = None
    iface.combat_log_offset = 0
    iface.combat_events = []
    iface.last_pet_health = 100
    iface.last_zone = ''
    iface.last_death_count = 0
    iface.last_dbm_timers = {}
    iface.pet_was_dead = False
    iface.radiant_queue = []
    iface._last_processed_event_id = 0
    iface.game_state = {}
    return iface


def _state(health=100, is_dead=False, dbm_timers=None, recent_events=None, chattyness=3, token='PET'):
    """Build a minimal game_state dict for trigger testing."""
    return {
        'pet': {'name': 'Rex', 'family': 'Wolf', 'pet_token': token, 'health': health, 'is_dead': is_dead},
        'zone': 'Elwynn Forest',
        'chattyness': chattyness,
        'nearby': {},
        'group_size': 0,
        'dbm_timers': dbm_timers or [],
        'recent_events': recent_events or [],
    }


# ── 1. Health Threshold Triggers ─────────────────────────────────────────────
class TestHealthThresholdTriggers(unittest.TestCase):

    def test_critical_health_trigger_fires_below_25(self):
        iface = make_interface()
        iface.game_state = _state(health=24)
        triggers = iface.check_radiant_triggers()
        texts = [t['text'] for t in triggers]
        self.assertTrue(
            any('critically wounded' in t.lower() or 'near death' in t.lower() for t in texts),
            f"Expected critical trigger, got: {texts}"
        )

    def test_critical_trigger_color_is_red(self):
        iface = make_interface()
        iface.game_state = _state(health=24)
        triggers = iface.check_radiant_triggers()
        critical = [t for t in triggers if 'critically wounded' in t['text'].lower() or 'near death' in t['text'].lower()]
        self.assertTrue(critical)
        self.assertEqual(critical[0]['color'], 'red')

    def test_injured_trigger_fires_below_50(self):
        iface = make_interface()
        iface.game_state = _state(health=49)
        triggers = iface.check_radiant_triggers()
        texts = [t['text'] for t in triggers]
        self.assertTrue(
            any('injured' in t.lower() for t in texts),
            f"Expected injured trigger, got: {texts}"
        )

    def test_injured_trigger_color_is_orange(self):
        iface = make_interface()
        iface.game_state = _state(health=49)
        triggers = iface.check_radiant_triggers()
        injured = [t for t in triggers if 'injured' in t['text'].lower()]
        self.assertTrue(injured)
        self.assertEqual(injured[0]['color'], 'orange')

    def test_healthy_pet_produces_no_health_trigger(self):
        iface = make_interface()
        iface.game_state = _state(health=100)
        triggers = iface.check_radiant_triggers()
        health_triggers = [t for t in triggers if 'injured' in t['text'].lower() or 'near death' in t['text'].lower()]
        self.assertFalse(health_triggers)

    def test_already_below_25_does_not_re_trigger(self):
        iface = make_interface()
        iface.last_pet_health = 20
        iface.game_state = _state(health=10)
        triggers = iface.check_radiant_triggers()
        texts = [t['text'] for t in triggers]
        self.assertFalse(
            any('near death' in t.lower() or 'critically wounded' in t.lower() for t in texts)
        )

    def test_already_below_50_does_not_re_trigger_injured(self):
        iface = make_interface()
        iface.last_pet_health = 40
        iface.game_state = _state(health=35)
        triggers = iface.check_radiant_triggers()
        texts = [t['text'] for t in triggers]
        self.assertFalse(any('injured' in t.lower() for t in texts))

    def test_last_pet_health_updated_after_check(self):
        iface = make_interface()
        iface.game_state = _state(health=30)
        iface.check_radiant_triggers()
        self.assertEqual(iface.last_pet_health, 30)

    def test_critical_threshold_boundary_exactly_25_does_not_fire(self):
        iface = make_interface()
        iface.game_state = _state(health=25)
        triggers = iface.check_radiant_triggers()
        texts = [t['text'] for t in triggers]
        self.assertFalse(any('near death' in t.lower() or 'critically wounded' in t.lower() for t in texts))

    def test_injured_threshold_boundary_exactly_50_does_not_fire(self):
        iface = make_interface()
        iface.game_state = _state(health=50)
        triggers = iface.check_radiant_triggers()
        texts = [t['text'] for t in triggers]
        self.assertFalse(any('injured' in t.lower() for t in texts))


# ── 2. Death Triggers ────────────────────────────────────────────────────────
class TestDeathTriggers(unittest.TestCase):

    def test_death_trigger_fires_on_first_death(self):
        iface = make_interface()
        iface.pet_was_dead = False
        iface.game_state = _state(health=0, is_dead=True)
        triggers = iface.check_radiant_triggers()
        texts = [t['text'] for t in triggers]
        self.assertTrue(
            any('fallen' in t.lower() or 'spirit' in t.lower() for t in texts),
            f"Expected death trigger, got: {texts}"
        )

    def test_death_trigger_color_is_red(self):
        iface = make_interface()
        iface.pet_was_dead = False
        iface.game_state = _state(health=0, is_dead=True)
        triggers = iface.check_radiant_triggers()
        death = [t for t in triggers if 'fallen' in t['text'].lower() or 'spirit' in t['text'].lower()]
        self.assertTrue(death)
        self.assertEqual(death[0]['color'], 'red')

    def test_death_trigger_does_not_fire_twice_while_still_dead(self):
        iface = make_interface()
        iface.pet_was_dead = False
        iface.game_state = _state(health=0, is_dead=True)
        iface.check_radiant_triggers()
        iface.game_state = _state(health=0, is_dead=True)
        triggers2 = iface.check_radiant_triggers()
        texts = [t['text'] for t in triggers2]
        self.assertFalse(
            any('fallen' in t.lower() or 'spirit' in t.lower() for t in texts)
        )

    def test_pet_was_dead_set_true_after_death(self):
        iface = make_interface()
        iface.pet_was_dead = False
        iface.game_state = _state(health=0, is_dead=True)
        iface.check_radiant_triggers()
        self.assertTrue(iface.pet_was_dead)

    def test_pet_was_dead_reset_when_alive_again(self):
        iface = make_interface()
        iface.pet_was_dead = True
        iface.game_state = _state(health=100, is_dead=False)
        iface.check_radiant_triggers()
        self.assertFalse(iface.pet_was_dead)

    def test_death_trigger_fires_again_after_resurrection(self):
        iface = make_interface()
        iface.pet_was_dead = False
        iface.game_state = _state(health=0, is_dead=True)
        iface.check_radiant_triggers()
        iface.game_state = _state(health=100, is_dead=False)
        iface.check_radiant_triggers()
        iface.game_state = _state(health=0, is_dead=True)
        triggers = iface.check_radiant_triggers()
        texts = [t['text'] for t in triggers]
        self.assertTrue(any('fallen' in t.lower() or 'spirit' in t.lower() for t in texts))

    def test_no_death_trigger_when_not_dead(self):
        iface = make_interface()
        iface.pet_was_dead = False
        iface.game_state = _state(health=80, is_dead=False)
        triggers = iface.check_radiant_triggers()
        texts = [t['text'] for t in triggers]
        self.assertFalse(any('fallen' in t.lower() or 'spirit' in t.lower() for t in texts))


# ── 3. DBM Boss Timer Triggers (SKIPPED — schema not implemented in Lua addon) ──
@unittest.skip(
    "DBM timer schema not yet implemented in MantellaWoW Lua addon.\n"
    "Current placeholder schema {id, time_remaining, message} does not match real DBM API.\n"
    "Real API: DBM:RegisterCallback('DBM_TimerUpdate', function(timer, elapsed, total))\n"
    "Reference: https://github.com/WeakAuras/WeakAuras2 (DBM trigger integration)\n"
    "Tracking issue: see GitHub Issues — 'Implement DBM_TimerUpdate callback in Lua addon'"
)
class TestDBMTimerTriggers(unittest.TestCase):

    def test_dbm_trigger_fires_when_time_drops_below_5(self):
        iface = make_interface()
        iface.last_dbm_timers = {'boss_slam': 10}
        timers = [{'id': 'boss_slam', 'time_remaining': 3, 'message': 'Slam'}]
        iface.game_state = _state(dbm_timers=timers)
        triggers = iface.check_radiant_triggers()
        texts = [t['text'] for t in triggers]
        self.assertTrue(
            any('brace' in t.lower() or 'slam' in t.lower() for t in texts),
            f"Expected DBM trigger, got: {texts}"
        )

    def test_dbm_trigger_color_is_red(self):
        iface = make_interface()
        iface.last_dbm_timers = {'boss_slam': 10}
        timers = [{'id': 'boss_slam', 'time_remaining': 3, 'message': 'Slam'}]
        iface.game_state = _state(dbm_timers=timers)
        triggers = iface.check_radiant_triggers()
        dbm_triggers = [t for t in triggers if 'brace' in t['text'].lower() or 'slam' in t['text'].lower()]
        self.assertTrue(dbm_triggers)
        self.assertEqual(dbm_triggers[0]['color'], 'red')

    def test_dbm_trigger_priority_is_urgent(self):
        iface = make_interface()
        iface.last_dbm_timers = {'boss_slam': 10}
        timers = [{'id': 'boss_slam', 'time_remaining': 3, 'message': 'Slam'}]
        iface.game_state = _state(dbm_timers=timers)
        triggers = iface.check_radiant_triggers()
        dbm_triggers = [t for t in triggers if 'brace' in t['text'].lower() or 'slam' in t['text'].lower()]
        self.assertEqual(dbm_triggers[0]['priority'], 'urgent')

    def test_dbm_trigger_does_not_refire_same_timer(self):
        iface = make_interface()
        iface.last_dbm_timers = {'boss_slam': 10}
        timers = [{'id': 'boss_slam', 'time_remaining': 3, 'message': 'Slam'}]
        iface.game_state = _state(dbm_timers=timers)
        iface.check_radiant_triggers()
        iface.game_state = _state(dbm_timers=timers)
        triggers2 = iface.check_radiant_triggers()
        texts = [t['text'] for t in triggers2]
        self.assertFalse(any('slam' in t.lower() for t in texts))

    def test_dbm_trigger_does_not_fire_when_time_still_above_5(self):
        iface = make_interface()
        iface.last_dbm_timers = {'boss_slam': 20}
        timers = [{'id': 'boss_slam', 'time_remaining': 8, 'message': 'Slam'}]
        iface.game_state = _state(dbm_timers=timers)
        triggers = iface.check_radiant_triggers()
        texts = [t['text'] for t in triggers]
        self.assertFalse(any('slam' in t.lower() for t in texts))

    def test_dbm_message_appears_in_trigger_text(self):
        iface = make_interface()
        iface.last_dbm_timers = {'void_zone': 15}
        timers = [{'id': 'void_zone', 'time_remaining': 2, 'message': 'Void Zone'}]
        iface.game_state = _state(dbm_timers=timers)
        triggers = iface.check_radiant_triggers()
        texts = [t['text'] for t in triggers]
        self.assertTrue(any('Void Zone' in t for t in texts))

    def test_dbm_timer_boundary_exactly_5_does_not_fire(self):
        iface = make_interface()
        iface.last_dbm_timers = {'boss_slam': 10}
        timers = [{'id': 'boss_slam', 'time_remaining': 5, 'message': 'Slam'}]
        iface.game_state = _state(dbm_timers=timers)
        triggers = iface.check_radiant_triggers()
        texts = [t['text'] for t in triggers]
        self.assertFalse(any('slam' in t.lower() for t in texts))

    def test_multiple_dbm_timers_all_fire_independently(self):
        iface = make_interface()
        iface.last_dbm_timers = {'a': 10, 'b': 10}
        timers = [
            {'id': 'a', 'time_remaining': 2, 'message': 'Ability A'},
            {'id': 'b', 'time_remaining': 3, 'message': 'Ability B'},
        ]
        iface.game_state = _state(dbm_timers=timers)
        triggers = iface.check_radiant_triggers()
        texts = ' '.join(t['text'] for t in triggers)
        self.assertIn('Ability A', texts)
        self.assertIn('Ability B', texts)

    def test_dbm_last_timers_updated_after_check(self):
        iface = make_interface()
        timers = [{'id': 'boss_slam', 'time_remaining': 8, 'message': 'Slam'}]
        iface.game_state = _state(dbm_timers=timers)
        iface.check_radiant_triggers()
        self.assertEqual(iface.last_dbm_timers.get('boss_slam'), 8)


# ── 4. Radiant Event Reaction Triggers ───────────────────────────────────────
class TestRadiantEventReactionTriggers(unittest.TestCase):

    def test_high_score_event_fires_reaction_trigger(self):
        iface = make_interface()
        events = [{'id': 1, 'type': 'combat', 'data': ''}]
        iface.game_state = _state(chattyness=3, recent_events=events)
        triggers = iface.check_radiant_triggers()
        reactive = [t for t in triggers if t.get('priority') == 'reactive']
        self.assertTrue(reactive, "Expected a reactive trigger for high-score combat event")

    def test_low_score_event_does_not_fire(self):
        iface = make_interface()
        events = [{'id': 1, 'type': 'chat', 'data': 'hello'}]
        iface.game_state = _state(chattyness=3, recent_events=events)
        triggers = iface.check_radiant_triggers()
        reactive = [t for t in triggers if t.get('priority') == 'reactive']
        self.assertFalse(reactive)

    def test_already_processed_event_is_skipped(self):
        iface = make_interface()
        iface._last_processed_event_id = 5
        events = [{'id': 5, 'type': 'combat', 'data': ''}]
        iface.game_state = _state(chattyness=3, recent_events=events)
        triggers = iface.check_radiant_triggers()
        reactive = [t for t in triggers if t.get('priority') == 'reactive']
        self.assertFalse(reactive)

    def test_new_event_id_advances_last_processed(self):
        iface = make_interface()
        iface._last_processed_event_id = 0
        events = [{'id': 7, 'type': 'combat', 'data': ''}]
        iface.game_state = _state(chattyness=3, recent_events=events)
        iface.check_radiant_triggers()
        self.assertEqual(iface._last_processed_event_id, 7)

    def test_reactive_trigger_color_is_cyan(self):
        iface = make_interface()
        events = [{'id': 1, 'type': 'combat', 'data': ''}]
        iface.game_state = _state(chattyness=3, recent_events=events)
        triggers = iface.check_radiant_triggers()
        reactive = [t for t in triggers if t.get('priority') == 'reactive']
        self.assertTrue(reactive)
        self.assertEqual(reactive[0]['color'], 'cyan')

    def test_reactive_trigger_text_starts_with_system(self):
        iface = make_interface()
        events = [{'id': 1, 'type': 'combat', 'data': ''}]
        iface.game_state = _state(chattyness=3, recent_events=events)
        triggers = iface.check_radiant_triggers()
        reactive = [t for t in triggers if t.get('priority') == 'reactive']
        self.assertTrue(reactive[0]['text'].startswith('[SYSTEM:'))

    def test_chattyness_5_fires_on_lower_score_event(self):
        iface = make_interface()
        events = [{'id': 1, 'type': 'zone', 'data': 'Stranglethorn Vale'}]
        iface.game_state = _state(chattyness=5, recent_events=events)
        triggers = iface.check_radiant_triggers()
        reactive = [t for t in triggers if t.get('priority') == 'reactive']
        self.assertTrue(reactive)

    def test_chattyness_1_only_fires_on_very_high_score(self):
        iface = make_interface()
        events = [{'id': 1, 'type': 'zone', 'data': 'Ironforge'}]
        iface.game_state = _state(chattyness=1, recent_events=events)
        triggers = iface.check_radiant_triggers()
        reactive = [t for t in triggers if t.get('priority') == 'reactive']
        self.assertFalse(reactive)

    def test_multiple_events_only_qualifying_fire(self):
        iface = make_interface()
        events = [
            {'id': 1, 'type': 'combat', 'data': ''},
            {'id': 2, 'type': 'chat',   'data': 'hi'},
        ]
        iface.game_state = _state(chattyness=3, recent_events=events)
        triggers = iface.check_radiant_triggers()
        reactive = [t for t in triggers if t.get('priority') == 'reactive']
        self.assertEqual(len(reactive), 1)


# ── 5. Radiant Queue Integration ─────────────────────────────────────────────
class TestRadiantQueueIntegration(unittest.TestCase):

    def test_process_radiant_triggers_appends_to_queue(self):
        iface = make_interface()
        iface.game_state = _state(health=24)
        iface._process_radiant_triggers()
        self.assertTrue(len(iface.radiant_queue) > 0)

    def test_process_radiant_triggers_updates_overlay(self):
        iface = make_interface()
        iface.game_state = _state(health=24)
        overlay_calls = []
        iface._update_overlay = lambda text, color='white': overlay_calls.append((text, color))
        iface._process_radiant_triggers()
        self.assertTrue(len(overlay_calls) > 0)

    def test_end_conversation_clears_radiant_queue(self):
        iface = make_interface()
        iface.radiant_queue = ['trigger one', 'trigger two']
        iface.end_conversation()
        self.assertEqual(iface.radiant_queue, [])

    def test_end_conversation_resets_last_processed_event_id(self):
        iface = make_interface()
        iface._last_processed_event_id = 99
        iface.end_conversation()
        self.assertEqual(iface._last_processed_event_id, 0)


# ── 6. Trigger Structure Validation ──────────────────────────────────────────
class TestTriggerStructure(unittest.TestCase):

    def _all_triggers(self, **state_kwargs):
        iface = make_interface()
        iface.game_state = _state(**state_kwargs)
        return iface.check_radiant_triggers()

    def test_health_trigger_has_required_keys(self):
        for t in self._all_triggers(health=24):
            self.assertIn('text', t)
            self.assertIn('priority', t)
            self.assertIn('color', t)

    def test_death_trigger_has_required_keys(self):
        for t in self._all_triggers(health=0, is_dead=True):
            self.assertIn('text', t)
            self.assertIn('priority', t)
            self.assertIn('color', t)

    def test_all_trigger_texts_are_non_empty_strings(self):
        iface = make_interface()
        iface.pet_was_dead = False
        iface.last_pet_health = 100
        states_to_test = [
            _state(health=24),
            _state(health=0, is_dead=True),
        ]
        for state in states_to_test:
            iface.game_state = state
            for t in iface.check_radiant_triggers():
                self.assertIsInstance(t['text'], str)
                self.assertTrue(t['text'].strip(), f"Empty trigger text in: {t}")


if __name__ == '__main__':
    unittest.main()
