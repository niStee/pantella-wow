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

## Retired Combat Log Watcher

The legacy combat-log subtype scraper (`_read_combat_log_delta`) has been replaced by the channel-neutral `CombatLogTransport` and the `C_ChatInfo.SendAddonMessageLogged` addon-message channel. See the `C_ChatInfo Addon Message APIs` section above and [`ADR-001`](ADR-001-ipc-transport.md) for the current architecture.

The `COMBAT_LOG_EVENT` family is still the underlying WoW event namespace; the `Wowpedia` reference below remains the canonical source for combat log event subtypes.

| Log event | Purpose | Source |
|---|---|---|
| `COMBAT_LOG_EVENT` | Combat log event namespace | [Wowpedia COMBAT_LOG_EVENT](https://wowpedia.fandom.com/wiki/COMBAT_LOG_EVENT) |

---

## C_ChatInfo Addon Message APIs (Primary Live-State Transport)

`C_ChatInfo.SendAddonMessageLogged` and `C_ChatInfo.RegisterAddonMessagePrefix` are the
primary live-state transport for the addon-to-backend IPC layer.
See [`ADR-001: Addon-to-Backend IPC Transport`](ADR-001-ipc-transport.md) for the full decision.

| API / Event | Used in | Primary Source | Blizzard Dev Portal |
|---|---|---|---|
| `C_ChatInfo.SendAddonMessageLogged(prefix, text, chatType, target)` | `SendPantellaMessage` (MantellaWoW.lua:72) | [Wowpedia (SendAddonMessage)](https://wowpedia.fandom.com/wiki/API_C_ChatInfo.SendAddonMessage) | [Dev Portal](https://develop.battle.net/documentation/world-of-warcraft) |
| `C_ChatInfo.RegisterAddonMessagePrefix(prefix)` | `InitializeAddon` (MantellaWoW.lua:376) | [Wowpedia](https://wowpedia.fandom.com/wiki/API_C_ChatInfo.RegisterAddonMessagePrefix) | [Dev Portal](https://develop.battle.net/documentation/world-of-warcraft) |

**Source comment in `MantellaWoW.lua`:**
```lua
-- Wowpedia: https://wowpedia.fandom.com/wiki/API_C_ChatInfo.SendAddonMessage
-- Sends a logged addon message that appears in WoWCombatLog.txt
-- Reuses the existing ToJSON() encoder; the encoded payload must stay under 255 bytes.
```

The `SendAddonMessageLogged` variant writes addon messages directly to `Logs/WoWCombatLog.txt`,
which the Python backend tails via `watchdog` polling. This is the same mechanism used by
WarcraftLogs, ACT, and other raid-logging tools, proven at scale with zero Win32 dependency.

**Payload limit:** 255 bytes per message (Blizzard-enforced). Chunking and sequence reassembly
are deferred to a future slice (see ADR-001 Milestones).

---

## Retired Win32 EditBox Prototype

WoW 12.0.7 exposes the main process window as `waApplication Window`, but addon-created Lua frames are not Win32 child controls. `EnumChildWindows` does not expose a Lua `EditBox`, so `WM_GETTEXT` and `WM_GETTEXTLENGTH` are not valid addon-to-backend IPC for live WoW state.

The accepted transport decision is documented in [`ADR-001: Addon-to-Backend IPC Transport`](ADR-001-ipc-transport.md):
combat-log addon messages are the primary live-state channel, pixel encoding is an optional
high-frequency supplement (not to be built speculatively), and SavedVariables are persistence/recovery only.

| Function | Purpose | Source |
|---|---|---|
| `WM_GETTEXT` | Legacy prototype for real Win32 text controls | Win32 API; retired for WoW Lua frames |
| `WM_GETTEXTLENGTH` | Legacy prototype for real Win32 text controls | Win32 API; retired for WoW Lua frames |
| `waApplication Window` | Current WoW 12.0.7 main window class | Valid capture target, not an IPC surface |

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
