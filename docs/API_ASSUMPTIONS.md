# API Assumptions & Verification Status

This document tracks every external API, event, or third-party schema assumption in the codebase.
Each entry must be verified against its canonical source before merging.

> **Rule:** If it doesn't have a source URL here, it doesn't get merged.
> **Enforced by:** `tests/test_api_assumptions.py` — will be red if any event/API lacks a source comment.

---

## Source of Truth Hierarchy (quick reference)

| Tier | Source | When to use |
|---|---|---|
| **1a** | In-game `/api` → `Blizzard_APIDocumentation` | Always current, no internet needed |
| **1b** | [Blizzard Developer Portal](https://develop.battle.net/documentation/world-of-warcraft) | REST/OAuth + post-10.1.7 Lua API reference |
| **1c** | [Townlong Yak FrameXML](https://www.townlong-yak.com/framexml/live) | Live FrameXML viewer, post-10.1.7 events |
| **2** | [Wowpedia](https://wowpedia.fandom.com/wiki/World_of_Warcraft_API) | Stable Classic-era APIs, lore, pet specs |
| **3** | Addon GitHub (BigWigs, DBM…) | Third-party addon schemas only |

> ⚠️ **Wowpedia is frozen after patch 10.1.7 (August 2023).** For APIs introduced or changed after that, use Tier 1b or 1c.

---

## Blizzard WoW Lua API (stable, verified)

All entries below are stable since Classic/Vanilla and verified via Wowpedia (Tier 2).
For any API added post-10.1.7, use Tier 1b (`develop.battle.net`) or 1c (Townlong Yak) as primary.

| API / Event | Used in | Primary Source | Blizzard Dev Portal | Status |
|---|---|---|---|---|
| `UnitHealth(unit)` | `check_radiant_triggers` | [Wowpedia](https://wowpedia.fandom.com/wiki/UnitHealth) | [Unit API](https://develop.battle.net/documentation/world-of-warcraft/game-data-apis) | ✅ |
| `UnitIsDeadOrGhost(unit)` | `check_radiant_triggers` | [Wowpedia](https://wowpedia.fandom.com/wiki/UnitIsDeadOrGhost) | [Unit API](https://develop.battle.net/documentation/world-of-warcraft/game-data-apis) | ✅ |
| `ZONE_CHANGED_NEW_AREA` | `_generate_reaction` — zone | [Wowpedia](https://wowpedia.fandom.com/wiki/ZONE_CHANGED_NEW_AREA) | [Dev Portal Events](https://develop.battle.net/documentation/world-of-warcraft) | ✅ |
| `PLAYER_REGEN_DISABLED` | `_generate_reaction` — combat | [Wowpedia](https://wowpedia.fandom.com/wiki/PLAYER_REGEN_DISABLED) | [Dev Portal Events](https://develop.battle.net/documentation/world-of-warcraft) | ✅ |
| `GOSSIP_SHOW` | `_generate_reaction` — gossip | [Wowpedia](https://wowpedia.fandom.com/wiki/GOSSIP_SHOW) | [Dev Portal Events](https://develop.battle.net/documentation/world-of-warcraft) | ✅ |
| `TRADE_SHOW` | `_generate_reaction` — trade | [Wowpedia](https://wowpedia.fandom.com/wiki/TRADE_SHOW) | [Dev Portal Events](https://develop.battle.net/documentation/world-of-warcraft) | ✅ |
| `QUEST_ACCEPTED` | `_generate_reaction` — quest_accepted | [Wowpedia](https://wowpedia.fandom.com/wiki/QUEST_ACCEPTED) | [Dev Portal Events](https://develop.battle.net/documentation/world-of-warcraft) | ✅ |
| `QUEST_TURNED_IN` | `_generate_reaction` — quest_complete | [Wowpedia](https://wowpedia.fandom.com/wiki/QUEST_TURNED_IN) | [Dev Portal Events](https://develop.battle.net/documentation/world-of-warcraft) | ✅ |
| `CHAT_MSG_SAY` | `_generate_reaction` — chat | [Wowpedia](https://wowpedia.fandom.com/wiki/CHAT_MSG_SAY) | [Dev Portal Events](https://develop.battle.net/documentation/world-of-warcraft) | ✅ |
| `COMBAT_LOG_EVENT` | `_read_combat_log_delta` | [Wowpedia](https://wowpedia.fandom.com/wiki/COMBAT_LOG_EVENT) | [Dev Portal Events](https://develop.battle.net/documentation/world-of-warcraft) | ✅ |
| `WM_GETTEXT` / `WM_GETTEXTLENGTH` | `_read_editbox_text` | Win32 API (stable) | N/A | ✅ |

### When Tier 1b (develop.battle.net) takes priority over Wowpedia

Use `develop.battle.net` as **primary** (and note it in the source comment) when:
- The API was added after patch **10.1.7 (August 2023)**
- The Wowpedia page shows outdated parameter counts or wrong return values
- You are implementing REST API calls (e.g. character lookups, realm status)
- Wowpedia says "needs updating" or has a `{{stub}}` tag

In those cases, the inline code comment format is:
```python
# Blizzard Dev Portal: https://develop.battle.net/documentation/world-of-warcraft
# (Wowpedia outdated for this API — use Dev Portal as primary)
```

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
    -- text     = ability name (e.g. "Void Zone")
    -- duration = total seconds (number)
    -- id       = unique bar identifier
end)
```

**Proposed serialization to EditBox JSON:**
```json
{"addon": "BigWigs", "id": "<id>", "name": "<text>", "duration": 12.0, "elapsed": 3.5}
```

**Why BigWigs is a better choice than DBM for this project:**
- ✅ Open, MIT-licensed, fully public GitHub API — no guesswork
- ✅ Simpler message schema (`text`, `duration`) vs DBM's opaque Lua timer objects
- ✅ `text` field = human-readable ability name, directly usable in trigger text
- ⚠️ Users need BigWigs installed (separate from DBM) — document in README

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

---

## Adding a New Pet / Guardian / Companion

See `.github/ISSUE_TEMPLATE/add_pet.yml` for the full checklist.
