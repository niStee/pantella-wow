"""
TDD: Wowpedia Source-of-Truth Validation Tests

These tests validate that:
1. All WoW APIs/Events used in the codebase are documented in wow_api_reference.json
2. All documented entries have required fields (name, wowpedia_url, valid)
3. All documented entries are marked as valid (not deprecated)
4. The reference file itself is well-formed

When a WoW patch deprecates an API:
- Set "valid": false in wow_api_reference.json
- The test will fail, forcing you to update the implementation

Wowpedia: https://wowpedia.fandom.com/wiki/Wowpedia
"""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
REF_FILE = REPO_ROOT / "docs" / "wow_api_reference.json"
WOW_PY = REPO_ROOT / "game_interfaces" / "wow.py"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_reference():
    """Load and return the parsed wow_api_reference.json."""
    assert REF_FILE.exists(), (
        f"Missing docs/wow_api_reference.json. "
        f"Create it following the Wowpedia source-of-truth workflow."
    )
    with open(REF_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def wow_py_source():
    """Return the raw source of game_interfaces/wow.py."""
    assert WOW_PY.exists(), "game_interfaces/wow.py not found"
    return WOW_PY.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def all_entries(api_reference):
    """Flatten all API/event entries across all categories."""
    entries = []
    skip_keys = {"_meta"}
    for key, value in api_reference.items():
        if key in skip_keys:
            continue
        assert isinstance(value, list), f"Expected list for key '{key}', got {type(value)}"
        entries.extend(value)
    return entries


# ── Schema Tests ──────────────────────────────────────────────────────────────

class TestReferenceSchema:
    """wow_api_reference.json must be well-formed and complete."""

    def test_reference_file_exists(self):
        """docs/wow_api_reference.json must exist."""
        assert REF_FILE.exists()

    def test_reference_has_meta(self, api_reference):
        """Reference file must have a _meta section."""
        assert "_meta" in api_reference
        meta = api_reference["_meta"]
        assert "source" in meta
        assert "wowpedia.fandom.com" in meta["source"]

    def test_meta_has_wow_version(self, api_reference):
        """_meta must specify the WoW version this was validated against."""
        assert "wow_version" in api_reference["_meta"]
        assert api_reference["_meta"]["wow_version"] != ""

    def test_meta_has_last_reviewed(self, api_reference):
        """_meta must have a last_reviewed date (YYYY-MM-DD)."""
        assert "last_reviewed" in api_reference["_meta"]
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        assert date_pattern.match(api_reference["_meta"]["last_reviewed"]), (
            f"last_reviewed must be YYYY-MM-DD, got: {api_reference['_meta']['last_reviewed']}"
        )

    def test_all_entries_have_required_fields(self, all_entries):
        """Every entry must have name, wowpedia_url, description, used_in, valid."""
        required = {"name", "wowpedia_url", "description", "used_in", "valid"}
        for entry in all_entries:
            missing = required - entry.keys()
            assert not missing, (
                f"Entry '{entry.get('name', '?')}' is missing fields: {missing}"
            )

    def test_all_wowpedia_urls_point_to_wowpedia(self, all_entries):
        """Every wowpedia_url must point to wowpedia.fandom.com."""
        for entry in all_entries:
            url = entry["wowpedia_url"]
            assert "wowpedia.fandom.com" in url, (
                f"Entry '{entry['name']}' has invalid wowpedia_url: {url}"
            )

    def test_all_used_in_are_non_empty(self, all_entries):
        """Every entry must reference at least one file location in used_in."""
        for entry in all_entries:
            assert isinstance(entry["used_in"], list), (
                f"Entry '{entry['name']}': used_in must be a list"
            )
            assert len(entry["used_in"]) > 0, (
                f"Entry '{entry['name']}': used_in must not be empty"
            )


# ── Validity Tests ────────────────────────────────────────────────────────────

class TestApiValidity:
    """All documented APIs/Events must be marked as valid (not deprecated)."""

    def test_no_deprecated_apis(self, all_entries):
        """
        All entries must have valid=true.

        When a WoW patch deprecates an API, set valid=false in wow_api_reference.json.
        This test will then fail, forcing you to either:
        - Update the implementation to use the new API, OR
        - Remove the feature if the API no longer exists
        """
        deprecated = [e["name"] for e in all_entries if not e.get("valid", True)]
        assert not deprecated, (
            f"Deprecated APIs found — update the implementation or remove them:\n"
            + "\n".join(f"  - {name}" for name in deprecated)
        )


# ── Coverage Tests ────────────────────────────────────────────────────────────

class TestCombatLogEventsCoverage:
    """Combat log event subtypes used in wow.py must all be in the reference."""

    KNOWN_COMBAT_LOG_SUBTYPES = [
        "SPELL_CAST_SUCCESS",
        "UNIT_DIED",
        "SPELL_AURA_APPLIED",
    ]

    def test_combat_log_events_section_exists(self, api_reference):
        assert "combat_log_events" in api_reference

    @pytest.mark.parametrize("event_name", KNOWN_COMBAT_LOG_SUBTYPES)
    def test_combat_log_event_documented(self, api_reference, event_name):
        """Each combat log event used in wow.py must be in the reference."""
        names = [e["name"] for e in api_reference["combat_log_events"]]
        assert event_name in names, (
            f"Combat log event '{event_name}' is used in wow.py but not documented in "
            f"docs/wow_api_reference.json. Add it with its Wowpedia URL."
        )

    @pytest.mark.parametrize("event_name", KNOWN_COMBAT_LOG_SUBTYPES)
    def test_combat_log_event_present_in_wow_py(self, wow_py_source, event_name):
        """Each documented combat log event must actually appear in wow.py."""
        assert event_name in wow_py_source, (
            f"Documented combat log event '{event_name}' not found in game_interfaces/wow.py. "
            f"Remove it from wow_api_reference.json if it is no longer used."
        )


class TestGameStateFieldsCoverage:
    """Game state fields documented in the reference must be used in wow.py."""

    KNOWN_FIELDS = [
        "player_name",
        "player_level",
        "zone",
        "in_combat",
        "group_size",
    ]

    def test_game_state_fields_section_exists(self, api_reference):
        assert "game_state_fields" in api_reference

    @pytest.mark.parametrize("field_name", KNOWN_FIELDS)
    def test_game_state_field_documented(self, api_reference, field_name):
        """Each game state field used in wow.py must be in the reference."""
        names = [e["name"] for e in api_reference["game_state_fields"]]
        assert field_name in names, (
            f"Game state field '{field_name}' is used in wow.py but not documented."
        )

    @pytest.mark.parametrize("field_name", KNOWN_FIELDS)
    def test_game_state_field_present_in_wow_py(self, wow_py_source, field_name):
        """Each documented game state field must appear in wow.py."""
        assert field_name in wow_py_source, (
            f"Documented field '{field_name}' not found in game_interfaces/wow.py."
        )


class TestPetApiFieldsCoverage:
    """Pet API fields documented in the reference must be used in wow.py."""

    KNOWN_PET_FIELDS = [
        "pet.name",
        "pet.family",
        "pet.health",
        "pet.is_dead",
        "pet.lore",
        "pet.pet_token",
    ]

    def test_pet_api_fields_section_exists(self, api_reference):
        assert "pet_api_fields" in api_reference

    @pytest.mark.parametrize("field_name", KNOWN_PET_FIELDS)
    def test_pet_field_documented(self, api_reference, field_name):
        """Each pet API field used in wow.py must be in the reference."""
        names = [e["name"] for e in api_reference["pet_api_fields"]]
        assert field_name in names, (
            f"Pet API field '{field_name}' is used in wow.py but not documented."
        )

    @pytest.mark.parametrize("field_name", KNOWN_PET_FIELDS)
    def test_pet_field_key_present_in_wow_py(self, wow_py_source, field_name):
        """Each documented pet field key must appear in wow.py source."""
        # Check for the dict key portion (e.g. 'name' from 'pet.name')
        key = field_name.split(".")[1]
        assert f"'{key}'" in wow_py_source or f'"{key}"' in wow_py_source, (
            f"Documented pet field key '{key}' (from '{field_name}') not found in wow.py."
        )


class TestRadiantEventTypesCoverage:
    """Radiant event types documented in the reference must be used in wow.py."""

    KNOWN_EVENT_TYPES = [
        "zone",
        "combat",
        "chat",
        "gossip_show",
        "trade_show",
        "quest_accepted",
        "quest_complete",
    ]

    def test_radiant_event_types_section_exists(self, api_reference):
        assert "radiant_event_types" in api_reference

    @pytest.mark.parametrize("event_type", KNOWN_EVENT_TYPES)
    def test_radiant_event_type_documented(self, api_reference, event_type):
        """Each radiant event type used in wow.py must be in the reference."""
        names = [e["name"] for e in api_reference["radiant_event_types"]]
        assert event_type in names, (
            f"Radiant event type '{event_type}' is used in wow.py but not documented."
        )

    @pytest.mark.parametrize("event_type", KNOWN_EVENT_TYPES)
    def test_radiant_event_type_present_in_wow_py(self, wow_py_source, event_type):
        """Each documented radiant event type must appear in wow.py."""
        assert f"'{event_type}'" in wow_py_source or f'"{event_type}"' in wow_py_source, (
            f"Documented event type '{event_type}' not found in game_interfaces/wow.py."
        )
