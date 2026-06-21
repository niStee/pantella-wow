"""
Static code analysis tests — API Assumption Enforcement

These tests do NOT run game code. They inspect the source of wow.py and
verify that every WoW Lua event and API function used has a Wowpedia
URL comment within 5 lines above its first use.

This enforces the rule from CONTRIBUTING.md:
  "If you can't link it, don't ship it."

Reference docs:
  https://wowpedia.fandom.com/wiki/World_of_Warcraft_API
  https://wowpedia.fandom.com/wiki/Events
  docs/LUA_EVENT_REFERENCE.md
  docs/API_ASSUMPTIONS.md
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
WOW_PY = REPO_ROOT / 'game_interfaces' / 'wow.py'


def _source():
    return WOW_PY.read_text(encoding='utf-8')


def _lines():
    return WOW_PY.read_text(encoding='utf-8').splitlines()


def _wowpedia_in_context(lines, line_index, window=6):
    """Return True if a wowpedia.fandom.com URL appears within `window` lines above line_index."""
    start = max(0, line_index - window)
    context = '\n'.join(lines[start:line_index])
    return 'wowpedia.fandom.com' in context


class TestLuaEventComments(unittest.TestCase):
    """
    Every WoW Lua event string used in wow.py must have a Wowpedia URL comment
    within 6 lines above its first occurrence.
    Source: https://wowpedia.fandom.com/wiki/Events
    """

    # Canonical events we use, mapped to their Wowpedia page
    # Source: docs/LUA_EVENT_REFERENCE.md
    REQUIRED_EVENTS = {
        'ZONE_CHANGED_NEW_AREA':  'https://wowpedia.fandom.com/wiki/ZONE_CHANGED_NEW_AREA',
        'PLAYER_REGEN_DISABLED':  'https://wowpedia.fandom.com/wiki/PLAYER_REGEN_DISABLED',
        'GOSSIP_SHOW':            'https://wowpedia.fandom.com/wiki/GOSSIP_SHOW',
        'TRADE_SHOW':             'https://wowpedia.fandom.com/wiki/TRADE_SHOW',
        'QUEST_ACCEPTED':         'https://wowpedia.fandom.com/wiki/QUEST_ACCEPTED',
        'QUEST_TURNED_IN':        'https://wowpedia.fandom.com/wiki/QUEST_TURNED_IN',
        'CHAT_MSG_SAY':           'https://wowpedia.fandom.com/wiki/CHAT_MSG_SAY',
        'COMBAT_LOG_EVENT':       'https://wowpedia.fandom.com/wiki/COMBAT_LOG_EVENT',
    }

    def test_all_required_event_urls_present_in_source(self):
        """Every required Wowpedia URL must appear somewhere in wow.py."""
        source = _source()
        missing = []
        for event, url in self.REQUIRED_EVENTS.items():
            if url not in source:
                missing.append(f"{event} -> {url}")
        self.assertFalse(
            missing,
            f"Missing Wowpedia comment URLs in wow.py:\n" + '\n'.join(missing)
        )

    def test_event_zone_changed_has_nearby_url(self):
        """ZONE_CHANGED_NEW_AREA must have its Wowpedia URL as a nearby comment."""
        lines = _lines()
        url = 'wowpedia.fandom.com/wiki/ZONE_CHANGED_NEW_AREA'
        for i, line in enumerate(lines):
            if 'ZONE_CHANGED_NEW_AREA' in line and 'http' not in line:
                self.assertTrue(
                    _wowpedia_in_context(lines, i),
                    f"No Wowpedia URL near 'ZONE_CHANGED_NEW_AREA' at line {i+1}"
                )

    def test_event_player_regen_disabled_has_nearby_url(self):
        lines = _lines()
        for i, line in enumerate(lines):
            if 'PLAYER_REGEN_DISABLED' in line and 'http' not in line:
                self.assertTrue(
                    _wowpedia_in_context(lines, i),
                    f"No Wowpedia URL near 'PLAYER_REGEN_DISABLED' at line {i+1}"
                )

    def test_event_gossip_show_has_nearby_url(self):
        lines = _lines()
        for i, line in enumerate(lines):
            if "'gossip_show'" in line and 'http' not in line:
                self.assertTrue(
                    _wowpedia_in_context(lines, i),
                    f"No Wowpedia URL near gossip_show at line {i+1}"
                )

    def test_event_quest_accepted_has_nearby_url(self):
        lines = _lines()
        for i, line in enumerate(lines):
            if "'quest_accepted'" in line and 'http' not in line:
                self.assertTrue(
                    _wowpedia_in_context(lines, i),
                    f"No Wowpedia URL near quest_accepted at line {i+1}"
                )

    def test_event_quest_complete_has_nearby_url(self):
        lines = _lines()
        for i, line in enumerate(lines):
            if "'quest_complete'" in line and 'http' not in line:
                self.assertTrue(
                    _wowpedia_in_context(lines, i),
                    f"No Wowpedia URL near quest_complete at line {i+1}"
                )

    def test_event_combat_log_has_nearby_url(self):
        lines = _lines()
        for i, line in enumerate(lines):
            if 'SPELL_CAST_SUCCESS' in line and 'http' not in line:
                self.assertTrue(
                    _wowpedia_in_context(lines, i),
                    f"No Wowpedia URL near SPELL_CAST_SUCCESS at line {i+1}"
                )


class TestUnitAPIComments(unittest.TestCase):
    """
    UnitHealth and UnitIsDeadOrGhost references must each have a
    Wowpedia URL comment in the surrounding code.
    Source: https://wowpedia.fandom.com/wiki/UnitHealth
            https://wowpedia.fandom.com/wiki/UnitIsDeadOrGhost
    """

    def test_unit_health_url_present(self):
        self.assertIn(
            'wowpedia.fandom.com/wiki/UnitHealth',
            _source()
        )

    def test_unit_is_dead_url_present(self):
        self.assertIn(
            'wowpedia.fandom.com/wiki/UnitIsDeadOrGhost',
            _source()
        )


class TestBigWigsSchemaDocumented(unittest.TestCase):
    """
    If BigWigs_StartBar is mentioned anywhere in the codebase (Lua or Python),
    the BigWigs GitHub URL must also be present in API_ASSUMPTIONS.md.
    """

    def test_bigwigs_schema_documented_in_api_assumptions(self):
        api_doc = (REPO_ROOT / 'docs' / 'API_ASSUMPTIONS.md').read_text(encoding='utf-8')
        self.assertIn(
            'github.com/BigWigsMods/BigWigs',
            api_doc,
            "BigWigs GitHub URL must be present in docs/API_ASSUMPTIONS.md"
        )

    def test_bigwigs_startbar_schema_documented(self):
        api_doc = (REPO_ROOT / 'docs' / 'API_ASSUMPTIONS.md').read_text(encoding='utf-8')
        self.assertIn('BigWigs_StartBar', api_doc)
        self.assertIn('duration', api_doc)

    def test_dbm_schema_documented_as_placeholder(self):
        """DBM must be documented in API_ASSUMPTIONS.md as not yet implemented."""
        api_doc = (REPO_ROOT / 'docs' / 'API_ASSUMPTIONS.md').read_text(encoding='utf-8')
        self.assertIn('DBM_TimerUpdate', api_doc)
        self.assertIn('NOT YET IMPLEMENTED', api_doc)


class TestContributingGuideCompleteness(unittest.TestCase):
    """CONTRIBUTING.md must reference all three source tiers."""

    @classmethod
    def setUpClass(cls):
        cls.contributing = (REPO_ROOT / 'CONTRIBUTING.md').read_text(encoding='utf-8')

    def test_blizzard_api_referenced(self):
        self.assertIn('townlong-yak.com', self.contributing)

    def test_wowpedia_referenced(self):
        self.assertIn('wowpedia.fandom.com', self.contributing)

    def test_dbm_github_referenced(self):
        self.assertIn('DeadlyBossMods', self.contributing)

    def test_bigwigs_github_referenced(self):
        self.assertIn('BigWigsMods', self.contributing)

    def test_wowpedia_freeze_warning_present(self):
        self.assertIn('10.1.7', self.contributing)


class TestLuaEventReferenceDoc(unittest.TestCase):
    """docs/LUA_EVENT_REFERENCE.md must exist and contain all canonical events."""

    @classmethod
    def setUpClass(cls):
        cls.doc = (REPO_ROOT / 'docs' / 'LUA_EVENT_REFERENCE.md').read_text(encoding='utf-8')

    def test_all_events_listed(self):
        required = [
            'ZONE_CHANGED_NEW_AREA',
            'PLAYER_REGEN_DISABLED',
            'GOSSIP_SHOW',
            'QUEST_ACCEPTED',
            'QUEST_TURNED_IN',
            'CHAT_MSG_SAY',
            'COMBAT_LOG_EVENT',
        ]
        for event in required:
            self.assertIn(event, self.doc, f"{event} missing from LUA_EVENT_REFERENCE.md")

    def test_bigwigs_schema_in_doc(self):
        self.assertIn('BigWigs_StartBar', self.doc)
        self.assertIn('BigWigs_StopBar', self.doc)

    def test_dbm_schema_in_doc(self):
        self.assertIn('DBM_TimerUpdate', self.doc)


if __name__ == '__main__':
    unittest.main()
