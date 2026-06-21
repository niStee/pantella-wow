# Lua Event & API Reference

This document lists every WoW Lua event and API function used in `game_interfaces/wow.py`,
with its canonical source URL.

All entries must also appear as an inline comment in the source code within 6 lines above their usage.
Enforced by `tests/test_api_assumptions.py`.

---

## Source of Truth for Lua Events

| Source | URL | Use when |
|---|---|---|
| **In-game `/api`** | `Blizzard_APIDocumentation` addon | Always current — primary reference |
| **Blizzard Dev Portal** | https://develop.battle.net/documentation/world-of-warcraft | APIs post-10.1.7, REST API, OAuth |
| **Townlong Yak FrameXML** | https://www.townlong-yak.com/framexml/live | Live viewer for any patch |
| **Wowpedia** | https://wowpedia.fandom.com/wiki/Events | Stable Classic-era events only (frozen after 10.1.7) |

> **Code comment format** when Blizzard Dev Portal is the primary source:
> ```python
> # Blizzard Dev Portal: https://develop.battle.net/documentation/world-of-warcraft
> # Wowpedia: https://wowpedia.fandom.com/wiki/SOME_EVENT  (secondary / may be outdated)
> ```
>
> **Code comment format** when Wowpedia is sufficient (stable pre-10.1.7 API):
> ```python
> # Wowpedia: https://wowpedia.fandom.com/wiki/SOME_EVENT
> ```

---

## Events Used in `_generate_reaction`

| Event type key | WoW Lua Event | Primary Source | Blizzard Dev Portal |
|---|---|---|---|
| `chat` | `CHAT_MSG_SAY` | [Wowpedia](https://wowpedia.fandom.com/wiki/CHAT_MSG_SAY) | [Dev Portal](https://develop.battle.net/documentation/world-of-warcraft) |
| `zone` | `ZONE_CHANGED_NEW_AREA` | [Wowpedia](https://wowpedia.fandom.com/wiki/ZONE_CHANGED_NEW_AREA) | [Dev Portal](https://develop.battle.net/documentation/world-of-warcraft) |
| `combat` | `PLAYER_REGEN_DISABLED` | [Wowpedia](https://wowpedia.fandom.com/wiki/PLAYER_REGEN_DISABLED) | [Dev Portal](https://develop.battle.net/documentation/world-of-warcraft) |
| `gossip_show` | `GOSSIP_SHOW` | [Wowpedia](https://wowpedia.fandom.com/wiki/GOSSIP_SHOW) | [Dev Portal](https://develop.battle.net/documentation/world-of-warcraft) |
| `trade_show` | `TRADE_SHOW` | [Wowpedia](https://wowpedia.fandom.com/wiki/TRADE_SHOW) | [Dev Portal](https://develop.battle.net/documentation/world-of-warcraft) |
| `quest_accepted` | `QUEST_ACCEPTED` | [Wowpedia](https://wowpedia.fandom.com/wiki/QUEST_ACCEPTED) | [Dev Portal](https://develop.battle.net/documentation/world-of-warcraft) |
| `quest_complete` | `QUEST_TURNED_IN` | [Wowpedia](https://wowpedia.fandom.com/wiki/QUEST_TURNED_IN) | [Dev Portal](https://develop.battle.net/documentation/world-of-warcraft) |

---

## Unit Query APIs in `check_radiant_triggers`

| Function | Purpose | Wowpedia | Blizzard Dev Portal |
|---|---|---|---|
| `UnitHealth("pet")` | Pet current HP | [Wowpedia](https://wowpedia.fandom.com/wiki/UnitHealth) | [Dev Portal](https://develop.battle.net/documentation/world-of-warcraft/game-data-apis) |
| `UnitIsDeadOrGhost("pet")` | Pet death detection | [Wowpedia](https://wowpedia.fandom.com/wiki/UnitIsDeadOrGhost) | [Dev Portal](https://develop.battle.net/documentation/world-of-warcraft/game-data-apis) |

---

## Combat Log Events in `_read_combat_log_delta`

| Log event | Purpose | Source |
|---|---|---|
| `SPELL_CAST_SUCCESS` | Ability cast tracking | [Wowpedia COMBAT_LOG_EVENT](https://wowpedia.fandom.com/wiki/COMBAT_LOG_EVENT) |
| `UNIT_DIED` | Death events | [Wowpedia COMBAT_LOG_EVENT](https://wowpedia.fandom.com/wiki/COMBAT_LOG_EVENT) |
| `SPELL_AURA_APPLIED` | Buff/debuff tracking | [Wowpedia COMBAT_LOG_EVENT](https://wowpedia.fandom.com/wiki/COMBAT_LOG_EVENT) |

---

## Win32 APIs in `_read_editbox_text`

| Function | Purpose | Source |
|---|---|---|
| `WM_GETTEXT` | Read EditBox text | Win32 API (stable, not WoW-specific) |
| `WM_GETTEXTLENGTH` | Get text buffer length | Win32 API |
| `GxWindowClass` | WoW main window class name | Stable since WoW 1.x |

---

## Third-Party Addon Timer Schemas

### BigWigs (recommended, verified)
Schema source: https://github.com/BigWigsMods/BigWigs/blob/master/Plugins/Bars.lua

```lua
BigWigsLoader:RegisterMessage("BigWigs_StartBar", function(event, module, id, text, duration, icon)
    -- text     = ability name string
    -- duration = total seconds (number)
    -- id       = bar identifier
end)
BigWigsLoader:RegisterMessage("BigWigs_StopBar", function(event, module, id, text) end)
```

### DBM (placeholder only, not implemented)
Callback source: https://github.com/WeakAuras/WeakAuras2
```lua
DBM:RegisterCallback("DBM_TimerUpdate", function(timer, elapsed, total) end)
```
See `docs/API_ASSUMPTIONS.md` for full status.
