# API Assumptions & Verification Status

This document tracks every external API, event, or third-party schema assumption in the codebase.
Each entry must be verified against its canonical source before merging.

> **Rule:** If it doesn't have a source URL here, it doesn't get merged.
> **Enforced by:** `tests/test_api_assumptions.py` — will be red if any event/API lacks a Wowpedia comment.

---

## Blizzard WoW Lua API (stable, verified)

All stable since Classic/Vanilla. Source: https://wowpedia.fandom.com/wiki/World_of_Warcraft_API

| API / Event | Used in | Wowpedia URL | Status |
|---|---|---|---|
| `UnitHealth(unit)` | `check_radiant_triggers` | https://wowpedia.fandom.com/wiki/UnitHealth | ✅ |
| `UnitIsDeadOrGhost(unit)` | `check_radiant_triggers` | https://wowpedia.fandom.com/wiki/UnitIsDeadOrGhost | ✅ |
| `ZONE_CHANGED_NEW_AREA` | `_generate_reaction` — zone | https://wowpedia.fandom.com/wiki/ZONE_CHANGED_NEW_AREA | ✅ |
| `PLAYER_REGEN_DISABLED` | `_generate_reaction` — combat | https://wowpedia.fandom.com/wiki/PLAYER_REGEN_DISABLED | ✅ |
| `GOSSIP_SHOW` | `_generate_reaction` — gossip | https://wowpedia.fandom.com/wiki/GOSSIP_SHOW | ✅ |
| `TRADE_SHOW` | `_generate_reaction` — trade | https://wowpedia.fandom.com/wiki/TRADE_SHOW | ✅ |
| `QUEST_ACCEPTED` | `_generate_reaction` — quest_accepted | https://wowpedia.fandom.com/wiki/QUEST_ACCEPTED | ✅ |
| `QUEST_TURNED_IN` | `_generate_reaction` — quest_complete | https://wowpedia.fandom.com/wiki/QUEST_TURNED_IN | ✅ |
| `CHAT_MSG_SAY` | `_generate_reaction` — chat | https://wowpedia.fandom.com/wiki/CHAT_MSG_SAY | ✅ |
| `COMBAT_LOG_EVENT` | `_read_combat_log_delta` | https://wowpedia.fandom.com/wiki/COMBAT_LOG_EVENT | ✅ |
| `WM_GETTEXT` / `WM_GETTEXTLENGTH` | `_read_editbox_text` | Win32 API (stable) | ✅ |

### Wowpedia Coverage Note

Wowpedia's API wiki was **partially frozen after patch 10.1.7 (August 2023)**.
For APIs added or changed after that patch, verify against:

1. In-game: `/api` → `Blizzard_APIDocumentation` (always current)
2. [Blizzard Developer Portal](https://develop.battle.net/documentation/world-of-warcraft)
3. [Townlong Yak live FrameXML viewer](https://www.townlong-yak.com/framexml/live)

---

## Third-Party Addon APIs

### ⚠️ DBM (Deadly Boss Mods) — NOT YET IMPLEMENTED IN LUA ADDON

Source: https://github.com/DeadlyBossMods/DBM-Retail
Callback reference: https://github.com/WeakAuras/WeakAuras2 (DBM trigger integration)

**Real callback signature (verified):**
```lua
DBM:RegisterCallback("DBM_TimerStart",  function(timer, name, time, spellId, type, ...) end)
DBM:RegisterCallback("DBM_TimerUpdate", function(timer, elapsed, total) end)
DBM:RegisterCallback("DBM_TimerStop",  function(id) end)
```

| Field | Placeholder (current) | Real DBM API | Status |
|---|---|---|---|
| Timer identifier | `timer['id']` (string) | `timer` Lua object | ❌ Wrong type |
| Time remaining | `timer['time_remaining']` | `total - elapsed` | ❌ Wrong key |
| Ability name | `timer['message']` | `name` (callback arg 1) | ❌ Wrong key |

**Required work before DBM tests can be un-skipped:**
1. Implement `DBM:RegisterCallback("DBM_TimerUpdate", ...)` in `MantellaWoW/MantellaWoW.lua`
2. Serialize as `{addon="DBM", name=name, elapsed=elapsed, total=total}` into EditBox JSON
3. Update `check_radiant_triggers` to use `total - elapsed`
4. Update test skip message with resolved issue number

---

### ✅ BigWigs (Alternative to DBM) — SCHEMA VERIFIED, NOT YET IMPLEMENTED

Source: https://github.com/BigWigsMods/BigWigs
Schema verified via: https://github.com/BigWigsMods/BigWigs/blob/master/Plugins/Bars.lua

**Real message signature (verified from source):**
```lua
-- Timer start: module fires this message
self:SendMessage("BigWigs_StartBar", module, id, text, duration, icon)

-- Timer stop
self:SendMessage("BigWigs_StopBar", module, id, text)

-- Listen to these from MantellaWoW.lua:
BigWigsLoader:RegisterMessage("BigWigs_StartBar", function(event, module, id, text, duration, icon)
    -- text   = ability name (e.g. "Void Zone")
    -- duration = total seconds (number)
    -- id     = unique bar identifier
end)
```

**Proposed serialization to EditBox JSON:**
```json
{"addon": "BigWigs", "id": "<id>", "name": "<text>", "duration": 12.0, "elapsed": 3.5}
```

**Why BigWigs is a better choice than DBM for this project:**
- ✅ Open, MIT-licensed, fully public GitHub API — no guesswork
- ✅ Simpler message schema (`text`, `duration`) vs DBM's opaque Lua timer objects
- ✅ Lower memory/CPU footprint than DBM (relevant during combat when overlay is active)
- ✅ `text` field = human-readable ability name, directly usable in trigger text
- ✅ 257 stars, 113 contributors, releases as recently as Sep 2025
- ⚠️ Users need BigWigs installed (separate install from DBM) — document in README

**Recommendation:** Implement BigWigs first. Add DBM as optional parallel path once BigWigs works.

---

## Hunter Pet Family → Specialization (Wowpedia-verified)

Source: https://wowpedia.fandom.com/wiki/Hunter_pet
Enforced by: `TestHunterSpecCorrectness` in `tests/test_wow_personalities.py`

| Spec | Families |
|---|---|
| **Ferocity** | Bat, Cat, Gorilla, Raptor, Ravager, Spider, Wind Serpent |
| **Tenacity** | Bear, Crab, Turtle, Wolf |
| **Cunning** | Bird of Prey, Boar, Fox, Hyena, Serpent |
| **Exotic Ferocity** | Core Hound, Devilsaur |
| **Exotic Tenacity** | Worm |

All families must have a `# https://wowpedia.fandom.com/wiki/...` comment in `wow.py`.
Enforced by `TestWowpediaSourceOfTruth` in `tests/test_wow_personalities.py`.

---

## Adding a New Pet / Guardian / Companion

See `.github/ISSUE_TEMPLATE/add_pet.yml` for the full checklist.
