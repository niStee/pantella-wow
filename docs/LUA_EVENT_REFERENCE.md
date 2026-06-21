# Lua Event & API Reference

This document lists every WoW Lua event and API function used in `game_interfaces/wow.py`,
with its canonical Wowpedia source URL.

All entries must also appear as an inline comment in the source code immediately above their usage.
Enforced by `tests/test_api_assumptions.py`.

> **Source hierarchy:** In-game `/api` > Townlong Yak > Wowpedia > nothing
> Wowpedia is partially frozen after patch 10.1.7 — verify newer APIs via Townlong Yak.

---

## Events Used in `_generate_reaction`

| Event type key | WoW Lua Event | Wowpedia URL |
|---|---|---|
| `chat` | `CHAT_MSG_SAY` | https://wowpedia.fandom.com/wiki/CHAT_MSG_SAY |
| `zone` | `ZONE_CHANGED_NEW_AREA` | https://wowpedia.fandom.com/wiki/ZONE_CHANGED_NEW_AREA |
| `combat` | `PLAYER_REGEN_DISABLED` | https://wowpedia.fandom.com/wiki/PLAYER_REGEN_DISABLED |
| `gossip_show` | `GOSSIP_SHOW` | https://wowpedia.fandom.com/wiki/GOSSIP_SHOW |
| `trade_show` | `TRADE_SHOW` | https://wowpedia.fandom.com/wiki/TRADE_SHOW |
| `quest_accepted` | `QUEST_ACCEPTED` | https://wowpedia.fandom.com/wiki/QUEST_ACCEPTED |
| `quest_complete` | `QUEST_TURNED_IN` | https://wowpedia.fandom.com/wiki/QUEST_TURNED_IN |

## Unit Query APIs Used in `check_radiant_triggers`

| Function | Purpose | Wowpedia URL |
|---|---|---|
| `UnitHealth("pet")` | Pet current HP | https://wowpedia.fandom.com/wiki/UnitHealth |
| `UnitIsDeadOrGhost("pet")` | Pet death detection | https://wowpedia.fandom.com/wiki/UnitIsDeadOrGhost |

## Combat Log Events Used in `_read_combat_log_delta`

| Log event | Purpose | Wowpedia URL |
|---|---|---|
| `SPELL_CAST_SUCCESS` | Ability cast tracking | https://wowpedia.fandom.com/wiki/COMBAT_LOG_EVENT |
| `UNIT_DIED` | Death events | https://wowpedia.fandom.com/wiki/COMBAT_LOG_EVENT |
| `SPELL_AURA_APPLIED` | Buff/debuff tracking | https://wowpedia.fandom.com/wiki/COMBAT_LOG_EVENT |

## Win32 APIs Used in `_read_editbox_text`

| Function | Purpose | Source |
|---|---|---|
| `WM_GETTEXT` | Read EditBox text from WoW window | Win32 API (not WoW-specific) |
| `WM_GETTEXTLENGTH` | Get text buffer length | Win32 API (not WoW-specific) |
| `GxWindowClass` | WoW main window class name | Stable since WoW 1.x |

---

## Third-Party Addon Timers

### BigWigs (recommended, verified)
Schema source: https://github.com/BigWigsMods/BigWigs/blob/master/Plugins/Bars.lua

```lua
-- Subscribe in MantellaWoW.lua:
BigWigsLoader:RegisterMessage("BigWigs_StartBar", function(event, module, id, text, duration, icon)
    -- text     = ability name string
    -- duration = total seconds (number)
    -- id       = bar identifier
end)
BigWigsLoader:RegisterMessage("BigWigs_StopBar", function(event, module, id, text) end)
```

### DBM (placeholder only, not implemented)
Callback source: https://github.com/WeakAuras/WeakAuras2 (DBM trigger integration)
```lua
DBM:RegisterCallback("DBM_TimerUpdate", function(timer, elapsed, total) end)
```
See `docs/API_ASSUMPTIONS.md` for full status.
