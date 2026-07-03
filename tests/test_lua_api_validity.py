"""
TDD: Wowpedia Source-of-Truth Validation for MantellaWoW Lua Addon

These tests validate that:
1. All WoW events registered in MantellaWoW.lua are documented with Wowpedia URLs
2. All documented Lua APIs appear in the actual MantellaWoW.lua source
3. Known deprecated/changed APIs are flagged
4. The Lua source registers the expected set of events (no undocumented additions)

Wowpedia: https://wowpedia.fandom.com/wiki/Wowpedia
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
LUA_FILE = REPO_ROOT / "MantellaWoW" / "MantellaWoW.lua"
LUA_DOCS = REPO_ROOT / "docs" / "wow_lua_api_used.md"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def lua_source():
    assert LUA_FILE.exists(), f"MantellaWoW.lua not found at {LUA_FILE}"
    return LUA_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def lua_docs_source():
    assert LUA_DOCS.exists(), (
        f"docs/wow_lua_api_used.md not found. "
        f"Create it following the Wowpedia source-of-truth workflow."
    )
    return LUA_DOCS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def registered_events(lua_source):
    """Extract all events passed to RegisterEvent() in the Lua source."""
    return set(re.findall(r'RegisterEvent\("([A-Z_]+)"\)', lua_source))


# ── Docs Existence Tests ─────────────────────────────────────────────────────────

class TestLuaDocsExist:
    """The Lua API docs file must exist and reference Wowpedia."""

    def test_lua_docs_file_exists(self):
        assert LUA_DOCS.exists()

    def test_lua_docs_references_wowpedia(self, lua_docs_source):
        assert "wowpedia.fandom.com" in lua_docs_source

    def test_lua_docs_has_last_reviewed(self, lua_docs_source):
        assert "Last reviewed" in lua_docs_source or "last reviewed" in lua_docs_source

    def test_lua_docs_has_deprecation_section(self, lua_docs_source):
        """Docs must have a deprecation watch section."""
        assert "Deprecation" in lua_docs_source or "deprecation" in lua_docs_source


# ── RegisterEvent Coverage Tests ────────────────────────────────────────────────────

# Canonical list of expected RegisterEvent calls — validated against Wowpedia.
# To add a new event: 1) find Wowpedia article, 2) add to this list AND lua_docs, 3) implement.
EXPECTED_REGISTERED_EVENTS = {
    "ADDON_LOADED",       # https://wowpedia.fandom.com/wiki/ADDON_LOADED
    "PLAYER_LOGIN",       # https://wowpedia.fandom.com/wiki/PLAYER_LOGIN
    "PLAYER_LOGOUT",      # https://wowpedia.fandom.com/wiki/PLAYER_LOGOUT
    "CHAT_MSG_SAY",       # https://wowpedia.fandom.com/wiki/CHAT_MSG_SAY
    "CHAT_MSG_PARTY",     # https://wowpedia.fandom.com/wiki/CHAT_MSG_PARTY
    "CHAT_MSG_WHISPER",   # https://wowpedia.fandom.com/wiki/CHAT_MSG_WHISPER
    "CHAT_MSG_EMOTE",     # https://wowpedia.fandom.com/wiki/CHAT_MSG_EMOTE
    "GOSSIP_SHOW",        # https://wowpedia.fandom.com/wiki/GOSSIP_SHOW
    "QUEST_ACCEPTED",     # https://wowpedia.fandom.com/wiki/QUEST_ACCEPTED
    "QUEST_COMPLETE",     # https://wowpedia.fandom.com/wiki/QUEST_COMPLETE
    "TRADE_SHOW",         # https://wowpedia.fandom.com/wiki/TRADE_SHOW
    "MERCHANT_SHOW",      # https://wowpedia.fandom.com/wiki/MERCHANT_SHOW
}


class TestRegisteredEventsCoverage:
    """All registered events must be in the expected set, and vice versa."""

    @pytest.mark.parametrize("event", sorted(EXPECTED_REGISTERED_EVENTS))
    def test_expected_event_is_registered(self, registered_events, event):
        """
        Each expected (Wowpedia-documented) event must be registered in the Lua source.
        If this fails, either add the RegisterEvent call or remove from EXPECTED_REGISTERED_EVENTS.
        """
        assert event in registered_events, (
            f"Event '{event}' is in the documented expected set but not found in MantellaWoW.lua. "
            f"Add RegisterEvent(\"{event}\") or remove it from EXPECTED_REGISTERED_EVENTS."
        )

    @pytest.mark.parametrize("event", sorted(EXPECTED_REGISTERED_EVENTS))
    def test_expected_event_documented_in_docs(self, lua_docs_source, event):
        """Each expected event must be documented with a Wowpedia link in wow_lua_api_used.md."""
        assert event in lua_docs_source, (
            f"Event '{event}' is registered in Lua but missing from docs/wow_lua_api_used.md. "
            f"Add it with its Wowpedia URL."
        )

    def test_no_undocumented_events_registered(self, registered_events):
        """
        No event should be registered in MantellaWoW.lua without being in EXPECTED_REGISTERED_EVENTS.
        This prevents silent addition of events without Wowpedia validation.
        """
        undocumented = registered_events - EXPECTED_REGISTERED_EVENTS
        assert not undocumented, (
            f"Events registered in MantellaWoW.lua but not documented:\n"
            + "\n".join(f"  - {e}" for e in sorted(undocumented))
            + "\nAdd them to EXPECTED_REGISTERED_EVENTS with a Wowpedia URL."
        )


# ── Lua API Coverage Tests ────────────────────────────────────────────────────────────

# All Lua API calls used in MantellaWoW.lua, validated against Wowpedia.
# Key = exact string that must appear in the Lua source.
# Value = Wowpedia URL for reference.
LUA_APIS = {
    # Unit APIs
    'UnitName("player")':              "https://wowpedia.fandom.com/wiki/UnitName",
    'UnitName("pet")':                 "https://wowpedia.fandom.com/wiki/UnitName",
    'UnitLevel("player")':             "https://wowpedia.fandom.com/wiki/UnitLevel",
    'UnitClass("player")':             "https://wowpedia.fandom.com/wiki/UnitClass",
    'UnitAffectingCombat("player")':   "https://wowpedia.fandom.com/wiki/UnitAffectingCombat",
    'UnitAffectingCombat("pet")':      "https://wowpedia.fandom.com/wiki/UnitAffectingCombat",
    'UnitIsDead("pet")':               "https://wowpedia.fandom.com/wiki/UnitIsDead",
    'UnitCreatureFamily("pet")':       "https://wowpedia.fandom.com/wiki/UnitCreatureFamily",
    'UnitCreatureType("pet")':         "https://wowpedia.fandom.com/wiki/UnitCreatureType",
    'UnitIsPlayer(':                   "https://wowpedia.fandom.com/wiki/UnitIsPlayer",
    'UnitReaction(':                   "https://wowpedia.fandom.com/wiki/UnitReaction",
    'UnitAura(':                       "https://wowpedia.fandom.com/wiki/UnitAura",
    'UnitHealthPercent(':              "https://wowpedia.fandom.com/wiki/UnitHealthPercent",
    # Zone & World
    'GetZoneText()':                   "https://wowpedia.fandom.com/wiki/GetZoneText",
    'GetSubZoneText()':                "https://wowpedia.fandom.com/wiki/GetSubZoneText",
    'IsInInstance()':                  "https://wowpedia.fandom.com/wiki/IsInInstance",
    'IsMounted()':                     "https://wowpedia.fandom.com/wiki/IsMounted",
    'GetTime()':                       "https://wowpedia.fandom.com/wiki/GetTime",
    # Group
    'GetNumGroupMembers()':            "https://wowpedia.fandom.com/wiki/GetNumGroupMembers",
    'HasPetSpells()':                  "https://wowpedia.fandom.com/wiki/HasPetSpells",
    # Namespace APIs
    'C_Timer.NewTicker(':             "https://wowpedia.fandom.com/wiki/C_Timer.NewTicker",
    'C_NamePlate.GetNamePlates()':    "https://wowpedia.fandom.com/wiki/C_NamePlate.GetNamePlates",
    'C_MountJournal.GetMountFromSpell(': "https://wowpedia.fandom.com/wiki/C_MountJournal.GetMountFromSpell",
    'C_PetJournal.GetSummonedPetGUID()': "https://wowpedia.fandom.com/wiki/C_PetJournal.GetSummonedPetGUID",
    'C_PetJournal.GetPetInfoByPetID(':   "https://wowpedia.fandom.com/wiki/C_PetJournal.GetPetInfoByPetID",
    'C_PetJournal.GetPetInfoBySpeciesID(': "https://wowpedia.fandom.com/wiki/C_PetJournal.GetPetInfoBySpeciesID",
    # Frame / Widget
    'CreateFrame(':                    "https://wowpedia.fandom.com/wiki/CreateFrame",
    'RegisterEvent(':                  "https://wowpedia.fandom.com/wiki/Frame:RegisterEvent",
    ':SetScript(':                     "https://wowpedia.fandom.com/wiki/Frame:SetScript",
    ':SetText(':                       "https://wowpedia.fandom.com/wiki/EditBox:SetText",
}


class TestLuaApiPresence:
    """
    Each documented Lua API call must actually appear in MantellaWoW.lua.
    If a test fails, the API was removed from the Lua source — update the docs.
    """

    @pytest.mark.parametrize("api_call,wowpedia_url", list(LUA_APIS.items()))
    def test_api_present_in_lua_source(self, lua_source, api_call, wowpedia_url):
        assert api_call in lua_source, (
            f"Documented Lua API '{api_call}' not found in MantellaWoW.lua.\n"
            f"Wowpedia: {wowpedia_url}\n"
            f"If removed intentionally, delete from LUA_APIS in this test file "
            f"and from docs/wow_lua_api_used.md."
        )


# ── Deprecation Watch Tests ───────────────────────────────────────────────────────

class TestDeprecationWatch:
    """
    APIs that changed in recent WoW patches and should be reviewed/migrated.
    These tests emit warnings (not failures) so CI doesn't block, but devs are notified.
    """

    def test_unit_aura_deprecation_notice(self, lua_source):
        """
        UnitAura() index-based API changed significantly in patch 10.1.
        The new preferred API is C_UnitAuras.GetAuraDataByIndex().
        Wowpedia: https://wowpedia.fandom.com/wiki/C_UnitAuras.GetAuraDataByIndex
        This test warns but does NOT fail — upgrade when convenient.
        """
        if 'UnitAura(' in lua_source:
            import warnings
            warnings.warn(
                "MantellaWoW.lua uses UnitAura() which changed in patch 10.1. "
                "Consider migrating to C_UnitAuras.GetAuraDataByIndex(). "
                "See: https://wowpedia.fandom.com/wiki/C_UnitAuras.GetAuraDataByIndex",
                DeprecationWarning,
                stacklevel=2,
            )

    def test_curve_constants_usage(self, lua_source):
        """
        CurveConstants.ScaleTo100 is used with UnitHealthPercent.
        Verify this constant still exists in the current WoW API.
        Wowpedia: https://wowpedia.fandom.com/wiki/UnitHealthPercent
        This test warns but does NOT fail.
        """
        if 'CurveConstants' in lua_source:
            import warnings
            warnings.warn(
                "MantellaWoW.lua uses CurveConstants.ScaleTo100 with UnitHealthPercent. "
                "Verify this constant is still valid in the current WoW version. "
                "See: https://wowpedia.fandom.com/wiki/UnitHealthPercent",
                DeprecationWarning,
                stacklevel=2,
            )
