# API Assumptions & Verification Status

This document tracks every external API, event, or third-party schema assumption in the codebase.
Each entry must be verified against its canonical source before merging.

> **Rule:** If it doesn't have a source URL here, it doesn't get merged.

---

## Blizzard WoW Lua API (stable)

These are native Blizzard APIs. Verified via Wowpedia. All stable since Classic/Vanilla.

| API / Event | Used in | Wowpedia URL | Status |
|---|---|---|---|
| `UnitHealth(unit)` | `check_radiant_triggers` — health thresholds | https://wowpedia.fandom.com/wiki/UnitHealth | ✅ Verified |
| `UnitIsDeadOrGhost(unit)` | `check_radiant_triggers` — death detection | https://wowpedia.fandom.com/wiki/UnitIsDeadOrGhost | ✅ Verified |
| `ZONE_CHANGED_NEW_AREA` | `_generate_reaction` event type `zone` | https://wowpedia.fandom.com/wiki/ZONE_CHANGED_NEW_AREA | ✅ Verified |
| `PLAYER_REGEN_DISABLED` | `_generate_reaction` event type `combat` | https://wowpedia.fandom.com/wiki/PLAYER_REGEN_DISABLED | ✅ Verified |
| `GOSSIP_SHOW` | `_generate_reaction` event type `gossip_show` | https://wowpedia.fandom.com/wiki/GOSSIP_SHOW | ✅ Verified |
| `QUEST_ACCEPTED` | `_generate_reaction` event type `quest_accepted` | https://wowpedia.fandom.com/wiki/QUEST_ACCEPTED | ✅ Verified |
| `QUEST_TURNED_IN` | `_generate_reaction` event type `quest_complete` | https://wowpedia.fandom.com/wiki/QUEST_TURNED_IN | ✅ Verified |
| `CHAT_MSG_SAY` | `_generate_reaction` event type `chat` | https://wowpedia.fandom.com/wiki/CHAT_MSG_SAY | ✅ Verified |
| `COMBAT_LOG_EVENT` | `_read_combat_log_delta` — log parsing | https://wowpedia.fandom.com/wiki/COMBAT_LOG_EVENT | ✅ Verified |
| `WM_GETTEXT` / `WM_GETTEXTLENGTH` | `_read_editbox_text` — Win32 EditBox scraping | Win32 API (not WoW-specific) | ✅ Stable Win32 |

---

## Wowpedia Coverage Note

Wowpedia's API wiki was **partially frozen after patch 10.1.7 (August 2023)**.
For APIs added or changed after that patch, verify against:

1. In-game: `/api` command → `Blizzard_APIDocumentation`
2. [Blizzard Developer Portal](https://develop.battle.net/documentation/world-of-warcraft)
3. [Townlong Yak API browser](https://www.townlong-yak.com/framexml/live) — live FrameXML viewer

---

## Third-Party Addon APIs

These are **not** Blizzard APIs. Wowpedia does not cover them.

### ⚠️ DBM (Deadly Boss Mods) — NOT YET IMPLEMENTED

| Field | Current placeholder | Real DBM API | Status |
|---|---|---|---|
| Timer identifier | `timer['id']` (string) | `timer` (Lua object) | ❌ Wrong type |
| Time remaining | `timer['time_remaining']` | `total - elapsed` (calculated) | ❌ Wrong key |
| Ability name | `timer['message']` | `name` (first callback arg) | ❌ Wrong key |

**Real callback signature** (verified via WeakAuras DBM integration):
```lua
-- Source: https://github.com/WeakAuras/WeakAuras2 (DBM trigger source)
DBM:RegisterCallback("DBM_TimerStart",  function(timer, name, time, spellId, type, ...) end)
DBM:RegisterCallback("DBM_TimerUpdate", function(timer, elapsed, total) end)
DBM:RegisterCallback("DBM_TimerStop",  function(id) end)
```

**Required work** before DBM tests can be un-skipped:
1. Implement `DBM:RegisterCallback("DBM_TimerUpdate", ...)` in `MantellaWoW/MantellaWoW.lua`
2. Serialize as `{name=name, elapsed=elapsed, total=total}` into the EditBox JSON
3. Update `check_radiant_triggers` to use `total - elapsed` instead of `time_remaining`
4. Update `last_dbm_timers` keyed by `name` instead of `id`

Tracked in: **GitHub Issue #TBD** — "Implement DBM_TimerUpdate callback in Lua addon"

---

## Hunter Pet Family → Specialization Map

Verified against: https://wowpedia.fandom.com/wiki/Hunter_pet

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

See `.github/ISSUE_TEMPLATE/add_pet.md` for the required checklist.
No PR adding a pet personality will be merged without:
- [ ] Wowpedia source URL as code comment
- [ ] Correct spec mentioned in the personality text
- [ ] Corresponding test in `TestHunterSpecCorrectness` or equivalent
