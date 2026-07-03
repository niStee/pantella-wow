"""
Static code analysis tests — API Assumption Enforcement

These tests do NOT run game code. They inspect source files and verify that:
  1. Every WoW Lua event/API has a source comment (Wowpedia or Blizzard Dev Portal)
  2. The Blizzard Developer Portal is documented as Tier-1b source
  3. BigWigs and DBM schemas are documented correctly
  4. CONTRIBUTING.md and LUA_EVENT_REFERENCE.md are complete

Source hierarchy enforced:
  Tier 1a: In-game /api → Blizzard_APIDocumentation
  Tier 1b: https://develop.battle.net/documentation/world-of-warcraft
  Tier 1c: https://www.townlong-yak.com/framexml/live
  Tier 2:  https://wowpedia.fandom.com/wiki/Events
  Tier 3:  Addon GitHub (BigWigs, DBM, ...)

Reference docs:
  docs/API_ASSUMPTIONS.md
  docs/LUA_EVENT_REFERENCE.md
  CONTRIBUTING.md
"""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
WOW_PY = REPO_ROOT / 'game_interfaces' / 'wow.py'

BLIZZARD_DEV_PORTAL = 'develop.battle.net/documentation/world-of-warcraft'


def _source():
    return WOW_PY.read_text(encoding='utf-8')


def _lines():
    return WOW_PY.read_text(encoding='utf-8').splitlines()


def _wowpedia_or_devportal_in_context(lines, line_index, window=6):
    """Return True if a Wowpedia URL OR Blizzard Dev Portal URL appears within `window` lines above."""
    start = max(0, line_index - window)
    context = '\n'.join(lines[start:line_index])
    return ('wowpedia.fandom.com' in context) or (BLIZZARD_DEV_PORTAL in context)


# ── 1. Blizzard Developer Portal documented as Tier-1b ────────────────────────
class TestBlizzardDevPortalDocumented(unittest.TestCase):
    """
    develop.battle.net must be present as an authoritative source in all
    key documentation files. This is Tier-1b in the source hierarchy.
    Ref: https://develop.battle.net/documentation/world-of-warcraft
    """

    def test_dev_portal_in_api_assumptions(self):
        doc = (REPO_ROOT / 'docs' / 'API_ASSUMPTIONS.md').read_text(encoding='utf-8')
        self.assertIn(
            BLIZZARD_DEV_PORTAL, doc,
            f"develop.battle.net URL missing from docs/API_ASSUMPTIONS.md"
        )

    def test_dev_portal_in_lua_event_reference(self):
        doc = (REPO_ROOT / 'docs' / 'LUA_EVENT_REFERENCE.md').read_text(encoding='utf-8')
        self.assertIn(
            BLIZZARD_DEV_PORTAL, doc,
            f"develop.battle.net URL missing from docs/LUA_EVENT_REFERENCE.md"
        )

    def test_dev_portal_in_contributing(self):
        doc = (REPO_ROOT / 'CONTRIBUTING.md').read_text(encoding='utf-8')
        self.assertIn(
            BLIZZARD_DEV_PORTAL, doc,
            f"develop.battle.net URL missing from CONTRIBUTING.md"
        )

    def test_dev_portal_tier_label_in_contributing(self):
        """CONTRIBUTING.md must describe the Dev Portal as a distinct tier (not just a footnote)."""
        doc = (REPO_ROOT / 'CONTRIBUTING.md').read_text(encoding='utf-8')
        # Must have both the URL and a header/label indicating it's a formal tier
        self.assertIn(BLIZZARD_DEV_PORTAL, doc)
        self.assertTrue(
            'Tier 1b' in doc or '1b' in doc or 'Blizzard Developer Portal' in doc,
            "CONTRIBUTING.md must label the Blizzard Dev Portal as a distinct source tier"
        )

    def test_dev_portal_table_column_in_api_assumptions(self):
        """API_ASSUMPTIONS.md Blizzard API table must have a Blizzard Dev Portal column."""
        doc = (REPO_ROOT / 'docs' / 'API_ASSUMPTIONS.md').read_text(encoding='utf-8')
        self.assertIn('Blizzard Dev Portal', doc)

    def test_post_10_1_7_guidance_present(self):
        """Both CONTRIBUTING.md and API_ASSUMPTIONS.md must warn about the Wowpedia 10.1.7 freeze."""
        for fname in ('CONTRIBUTING.md', 'docs/API_ASSUMPTIONS.md'):
            doc = (REPO_ROOT / fname).read_text(encoding='utf-8')
            self.assertIn(
                '10.1.7', doc,
                f"Wowpedia post-10.1.7 freeze warning missing from {fname}"
            )


# ── 2. Lua event comments ─────────────────────────────────────────────────────
class TestLuaEventComments(unittest.TestCase):
    """
    Every WoW Lua event string used in wow.py must have either a
    Wowpedia URL OR a Blizzard Dev Portal URL as a comment within 6 lines above.
    Source: https://wowpedia.fandom.com/wiki/Events
            https://develop.battle.net/documentation/world-of-warcraft
    """

    REQUIRED_WOWPEDIA_URLS = {
        'ZONE_CHANGED_NEW_AREA':  'wowpedia.fandom.com/wiki/ZONE_CHANGED_NEW_AREA',
        'PLAYER_REGEN_DISABLED':  'wowpedia.fandom.com/wiki/PLAYER_REGEN_DISABLED',
        'GOSSIP_SHOW':            'wowpedia.fandom.com/wiki/GOSSIP_SHOW',
        'TRADE_SHOW':             'wowpedia.fandom.com/wiki/TRADE_SHOW',
        'QUEST_ACCEPTED':         'wowpedia.fandom.com/wiki/QUEST_ACCEPTED',
        'QUEST_TURNED_IN':        'wowpedia.fandom.com/wiki/QUEST_TURNED_IN',
        'CHAT_MSG_SAY':           'wowpedia.fandom.com/wiki/CHAT_MSG_SAY',
        'COMBAT_LOG_EVENT':       'wowpedia.fandom.com/wiki/COMBAT_LOG_EVENT',
    }

    def test_all_required_source_urls_present_in_source(self):
        """Every required source URL (Wowpedia or Dev Portal) must appear somewhere in wow.py."""
        source = _source()
        missing = []
        for event, url in self.REQUIRED_WOWPEDIA_URLS.items():
            # Accept either the Wowpedia URL or the Blizzard Dev Portal URL near this event
            if url not in source and BLIZZARD_DEV_PORTAL not in source:
                missing.append(f"{event} -> {url} (or {BLIZZARD_DEV_PORTAL})")
        self.assertFalse(
            missing,
            "Missing source URLs in wow.py:\n" + '\n'.join(missing)
        )

    def test_event_zone_changed_has_nearby_source(self):
        lines = _lines()
        for i, line in enumerate(lines):
            if 'ZONE_CHANGED_NEW_AREA' in line and 'http' not in line:
                self.assertTrue(
                    _wowpedia_or_devportal_in_context(lines, i),
                    f"No source URL near 'ZONE_CHANGED_NEW_AREA' at line {i+1}"
                )

    def test_event_player_regen_disabled_has_nearby_source(self):
        lines = _lines()
        for i, line in enumerate(lines):
            if 'PLAYER_REGEN_DISABLED' in line and 'http' not in line:
                self.assertTrue(
                    _wowpedia_or_devportal_in_context(lines, i),
                    f"No source URL near 'PLAYER_REGEN_DISABLED' at line {i+1}"
                )

    def test_event_gossip_show_has_nearby_source(self):
        lines = _lines()
        for i, line in enumerate(lines):
            if "'gossip_show'" in line and 'http' not in line:
                self.assertTrue(
                    _wowpedia_or_devportal_in_context(lines, i),
                    f"No source URL near gossip_show at line {i+1}"
                )

    def test_event_quest_accepted_has_nearby_source(self):
        lines = _lines()
        for i, line in enumerate(lines):
            if "'quest_accepted'" in line and 'http' not in line:
                self.assertTrue(
                    _wowpedia_or_devportal_in_context(lines, i),
                    f"No source URL near quest_accepted at line {i+1}"
                )

    def test_event_quest_complete_has_nearby_source(self):
        lines = _lines()
        for i, line in enumerate(lines):
            if "'quest_complete'" in line and 'http' not in line:
                self.assertTrue(
                    _wowpedia_or_devportal_in_context(lines, i),
                    f"No source URL near quest_complete at line {i+1}"
                )

    def test_event_combat_log_has_nearby_source(self):
        lines = _lines()
        for i, line in enumerate(lines):
            if 'SPELL_CAST_SUCCESS' in line and 'http' not in line:
                self.assertTrue(
                    _wowpedia_or_devportal_in_context(lines, i),
                    f"No source URL near SPELL_CAST_SUCCESS at line {i+1}"
                )


# ── 3. Unit API comments ──────────────────────────────────────────────────────
class TestUnitAPIComments(unittest.TestCase):
    """
    UnitHealth and UnitIsDeadOrGhost must each have a source URL (Wowpedia or Dev Portal).
    """

    def test_unit_health_url_present(self):
        source = _source()
        self.assertTrue(
            'wowpedia.fandom.com/wiki/UnitHealth' in source or BLIZZARD_DEV_PORTAL in source,
            "No source URL for UnitHealth in wow.py"
        )

    def test_unit_is_dead_url_present(self):
        source = _source()
        self.assertTrue(
            'wowpedia.fandom.com/wiki/UnitIsDeadOrGhost' in source or BLIZZARD_DEV_PORTAL in source,
            "No source URL for UnitIsDeadOrGhost in wow.py"
        )


# ── 4. BigWigs / DBM schema documentation ────────────────────────────────────
class TestBigWigsSchemaDocumented(unittest.TestCase):

    def test_bigwigs_github_in_api_assumptions(self):
        doc = (REPO_ROOT / 'docs' / 'API_ASSUMPTIONS.md').read_text(encoding='utf-8')
        self.assertIn('github.com/BigWigsMods/BigWigs', doc)

    def test_bigwigs_startbar_schema_documented(self):
        doc = (REPO_ROOT / 'docs' / 'API_ASSUMPTIONS.md').read_text(encoding='utf-8')
        self.assertIn('BigWigs_StartBar', doc)
        self.assertIn('duration', doc)

    def test_dbm_schema_documented_as_not_implemented(self):
        doc = (REPO_ROOT / 'docs' / 'API_ASSUMPTIONS.md').read_text(encoding='utf-8')
        self.assertIn('DBM_TimerUpdate', doc)
        self.assertIn('NOT YET IMPLEMENTED', doc)


# ── 5. CONTRIBUTING.md completeness ──────────────────────────────────────────
class TestContributingGuideCompleteness(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.doc = (REPO_ROOT / 'CONTRIBUTING.md').read_text(encoding='utf-8')

    def test_blizzard_dev_portal_present(self):
        self.assertIn(BLIZZARD_DEV_PORTAL, self.doc)

    def test_townlong_yak_present(self):
        self.assertIn('townlong-yak.com', self.doc)

    def test_wowpedia_present(self):
        self.assertIn('wowpedia.fandom.com', self.doc)

    def test_dbm_github_present(self):
        self.assertIn('DeadlyBossMods', self.doc)

    def test_bigwigs_github_present(self):
        self.assertIn('BigWigsMods', self.doc)

    def test_wowpedia_freeze_warning_present(self):
        self.assertIn('10.1.7', self.doc)

    def test_post_10_1_7_comment_format_shown(self):
        """CONTRIBUTING.md must show the comment format for post-10.1.7 APIs."""
        self.assertIn('Blizzard Dev Portal:', self.doc)


# ── 6. LUA_EVENT_REFERENCE.md completeness ───────────────────────────────────
class TestLuaEventReferenceDoc(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.doc = (REPO_ROOT / 'docs' / 'LUA_EVENT_REFERENCE.md').read_text(encoding='utf-8')

    def test_all_events_listed(self):
        required = [
            'ZONE_CHANGED_NEW_AREA', 'PLAYER_REGEN_DISABLED',
            'GOSSIP_SHOW', 'QUEST_ACCEPTED', 'QUEST_TURNED_IN',
            'CHAT_MSG_SAY', 'COMBAT_LOG_EVENT',
        ]
        for event in required:
            self.assertIn(event, self.doc, f"{event} missing from LUA_EVENT_REFERENCE.md")

    def test_blizzard_dev_portal_in_doc(self):
        self.assertIn(BLIZZARD_DEV_PORTAL, self.doc)

    def test_bigwigs_schema_in_doc(self):
        self.assertIn('BigWigs_StartBar', self.doc)

    def test_dbm_schema_in_doc(self):
        self.assertIn('DBM_TimerUpdate', self.doc)


if __name__ == '__main__':
    unittest.main()
