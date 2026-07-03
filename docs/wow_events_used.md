# WoW Events & APIs Used in pantella-wow

> **Source of Truth:** [Wowpedia](https://wowpedia.fandom.com/wiki/Wowpedia)  
> **Last reviewed:** 2026-06-22  
> **WoW version:** 11.x (The War Within)

All WoW APIs and Events listed here are validated against Wowpedia.
When adding new APIs/Events, always:
1. Find the Wowpedia article first
2. Add the entry to [`docs/wow_api_reference.json`](./wow_api_reference.json)
3. Write a failing test in `tests/test_wow_api_validity.py` first (TDD)
4. Then implement the feature

---

## Combat Log Events

These are subtypes of [`COMBAT_LOG_EVENT_UNFILTERED`](https://wowpedia.fandom.com/wiki/COMBAT_LOG_EVENT)
parsed directly from `WoWCombatLog.txt`.

| Event | Wowpedia | Used In |
|---|---|---|
| `SPELL_CAST_SUCCESS` | [link](https://wowpedia.fandom.com/wiki/COMBAT_LOG_EVENT) | `wow.py:_read_combat_log_delta` |
| `UNIT_DIED` | [link](https://wowpedia.fandom.com/wiki/COMBAT_LOG_EVENT) | `wow.py:_read_combat_log_delta` |
| `SPELL_AURA_APPLIED` | [link](https://wowpedia.fandom.com/wiki/COMBAT_LOG_EVENT) | `wow.py:_read_combat_log_delta` |

---

## Game State Fields (Lua → Python via EditBox)

These fields are populated by the `MantellaWoW` Lua addon and read via the Win32 EditBox scraper.

| Field | Lua Source | Wowpedia | Used In |
|---|---|---|---|
| `player_name` | `UnitName('player')` | [link](https://wowpedia.fandom.com/wiki/UnitName) | `get_current_context_string` |
| `player_level` | `UnitLevel('player')` | [link](https://wowpedia.fandom.com/wiki/UnitLevel) | `get_current_context_string` |
| `zone` | `GetZoneText()` | [link](https://wowpedia.fandom.com/wiki/GetZoneText) | `get_system_prompt` |
| `in_combat` | `UnitAffectingCombat('player')` | [link](https://wowpedia.fandom.com/wiki/UnitAffectingCombat) | `get_current_context_string` |
| `group_size` | `GetNumGroupMembers()` | [link](https://wowpedia.fandom.com/wiki/GetNumGroupMembers) | `get_system_prompt` |

---

## Pet API Fields

| Field | Lua Source | Wowpedia | Used In |
|---|---|---|---|
| `pet.name` | `UnitName('pet')` | [link](https://wowpedia.fandom.com/wiki/UnitName) | `get_system_prompt` |
| `pet.family` | `UnitCreatureFamily('pet')` | [link](https://wowpedia.fandom.com/wiki/UnitCreatureFamily) | `get_system_prompt` |
| `pet.health` | `UnitHealth('pet') / UnitHealthMax('pet')` | [link](https://wowpedia.fandom.com/wiki/UnitHealth) | `check_radiant_triggers` |
| `pet.is_dead` | `UnitIsDeadOrGhost('pet')` | [link](https://wowpedia.fandom.com/wiki/UnitIsDeadOrGhost) | `check_radiant_triggers` |
| `pet.lore` | `C_PetJournal.GetPetInfoByPetID()` | [link](https://wowpedia.fandom.com/wiki/C_PetJournal.GetPetInfoByPetID) | `get_system_prompt` |
| `pet.pet_token` | custom (PET/MOUNT/COMPANION) | [link](https://wowpedia.fandom.com/wiki/UnitClassification) | `_score_event` |

---

## Radiant Trigger Event Types

These event types are sent from the Lua addon and mapped to WoW events.

| Event Type | WoW Event | Wowpedia | Used In |
|---|---|---|---|
| `zone` | `ZONE_CHANGED_NEW_AREA` | [link](https://wowpedia.fandom.com/wiki/ZONE_CHANGED_NEW_AREA) | `_generate_reaction` |
| `combat` | `PLAYER_REGEN_DISABLED` | [link](https://wowpedia.fandom.com/wiki/PLAYER_REGEN_DISABLED) | `_generate_reaction` |
| `chat` | `CHAT_MSG_SAY` | [link](https://wowpedia.fandom.com/wiki/CHAT_MSG_SAY) | `_generate_reaction` |
| `gossip_show` | `GOSSIP_SHOW` | [link](https://wowpedia.fandom.com/wiki/GOSSIP_SHOW) | `_generate_reaction` |
| `trade_show` | `TRADE_SHOW` | [link](https://wowpedia.fandom.com/wiki/TRADE_SHOW) | `_generate_reaction` |
| `quest_accepted` | `QUEST_ACCEPTED` | [link](https://wowpedia.fandom.com/wiki/QUEST_ACCEPTED) | `_generate_reaction` |
| `quest_complete` | `QUEST_TURNED_IN` | [link](https://wowpedia.fandom.com/wiki/QUEST_TURNED_IN) | `_generate_reaction` |

---

## Adding New APIs/Events — Checklist

- [ ] Wowpedia article exists and API is marked as available in current WoW version
- [ ] Entry added to `docs/wow_api_reference.json` with `"valid": true`
- [ ] Failing test added to `tests/test_wow_api_validity.py`
- [ ] Implementation done
- [ ] Test passes
- [ ] This file updated
