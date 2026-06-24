# WoW Lua API Used in MantellaWoW.lua

> **Source of Truth:** [Wowpedia](https://wowpedia.fandom.com/wiki/Wowpedia)  
> **Last reviewed:** 2026-06-22  
> **WoW version:** 11.x (The War Within)

All Lua APIs and Events registered in `MantellaWoW/MantellaWoW.lua` are validated against Wowpedia.
When adding new APIs, always follow the TDD workflow in [`docs/wow_events_used.md`](./wow_events_used.md).

---

## Registered Events (Frame:RegisterEvent)

| Event | Wowpedia | Used In | Notes |
|---|---|---|---|
| `ADDON_LOADED` | [link](https://wowpedia.fandom.com/wiki/ADDON_LOADED) | `frame:SetScript OnEvent` | Triggers `InitializeAddon()` |
| `PLAYER_LOGIN` | [link](https://wowpedia.fandom.com/wiki/PLAYER_LOGIN) | `frame:SetScript OnEvent` | Starts `C_Timer.NewTicker` |
| `PLAYER_LOGOUT` | [link](https://wowpedia.fandom.com/wiki/PLAYER_LOGOUT) | `frame:SetScript OnEvent` | Final state flush |
| `CHAT_MSG_SAY` | [link](https://wowpedia.fandom.com/wiki/CHAT_MSG_SAY) | `chatFrame:SetScript OnEvent` | Pushes `chat` radiant event |
| `CHAT_MSG_PARTY` | [link](https://wowpedia.fandom.com/wiki/CHAT_MSG_PARTY) | `chatFrame:SetScript OnEvent` | Pushes `chat` radiant event |
| `CHAT_MSG_WHISPER` | [link](https://wowpedia.fandom.com/wiki/CHAT_MSG_WHISPER) | `chatFrame:SetScript OnEvent` | Pushes `chat` radiant event |
| `CHAT_MSG_EMOTE` | [link](https://wowpedia.fandom.com/wiki/CHAT_MSG_EMOTE) | `chatFrame:SetScript OnEvent` | Pushes `chat` radiant event |
| `GOSSIP_SHOW` | [link](https://wowpedia.fandom.com/wiki/GOSSIP_SHOW) | `interactionFrame:SetScript OnEvent` | Pushes `gossip_show` event |
| `QUEST_ACCEPTED` | [link](https://wowpedia.fandom.com/wiki/QUEST_ACCEPTED) | `interactionFrame:SetScript OnEvent` | Pushes `quest_accepted` event |
| `QUEST_COMPLETE` | [link](https://wowpedia.fandom.com/wiki/QUEST_COMPLETE) | `interactionFrame:SetScript OnEvent` | Pushes `quest_complete` event |
| `TRADE_SHOW` | [link](https://wowpedia.fandom.com/wiki/TRADE_SHOW) | `interactionFrame:SetScript OnEvent` | Pushes `trade_show` event |
| `MERCHANT_SHOW` | [link](https://wowpedia.fandom.com/wiki/MERCHANT_SHOW) | `interactionFrame:SetScript OnEvent` | Pushes merchant event |

---

## Unit APIs

| API | Wowpedia | Used In |
|---|---|---|
| `UnitName("player")` | [link](https://wowpedia.fandom.com/wiki/UnitName) | `UpdatePlayerState` |
| `UnitName("pet")` | [link](https://wowpedia.fandom.com/wiki/UnitName) | `GetCurrentCompanion` |
| `UnitName("npc")` | [link](https://wowpedia.fandom.com/wiki/UnitName) | `interactionFrame OnEvent` |
| `UnitName("target")` | [link](https://wowpedia.fandom.com/wiki/UnitName) | `interactionFrame OnEvent` |
| `UnitName("pettarget")` | [link](https://wowpedia.fandom.com/wiki/UnitName) | `GetCurrentCompanion` |
| `UnitLevel("player")` | [link](https://wowpedia.fandom.com/wiki/UnitLevel) | `UpdatePlayerState` |
| `UnitClass("player")` | [link](https://wowpedia.fandom.com/wiki/UnitClass) | `UpdatePlayerState` |
| `UnitAffectingCombat("player")` | [link](https://wowpedia.fandom.com/wiki/UnitAffectingCombat) | `UpdatePlayerState` |
| `UnitAffectingCombat("pet")` | [link](https://wowpedia.fandom.com/wiki/UnitAffectingCombat) | `GetCurrentCompanion` |
| `UnitIsDead("pet")` | [link](https://wowpedia.fandom.com/wiki/UnitIsDead) | `GetCurrentCompanion` |
| `UnitCreatureFamily("pet")` | [link](https://wowpedia.fandom.com/wiki/UnitCreatureFamily) | `GetCurrentCompanion` |
| `UnitCreatureType("pet")` | [link](https://wowpedia.fandom.com/wiki/UnitCreatureType) | `GetCurrentCompanion` |
| `UnitIsPlayer(unit)` | [link](https://wowpedia.fandom.com/wiki/UnitIsPlayer) | `UpdateSocialState` |
| `UnitReaction("player", unit)` | [link](https://wowpedia.fandom.com/wiki/UnitReaction) | `UpdateSocialState` |
| `UnitAura("player", i)` | [link](https://wowpedia.fandom.com/wiki/UnitAura) | `GetCurrentCompanion` (mount detection) |
| `UnitHealthPercent("pet", ...)` | [link](https://wowpedia.fandom.com/wiki/UnitHealthPercent) | `GetCurrentCompanion` |

---

## Zone & World APIs

| API | Wowpedia | Used In |
|---|---|---|
| `GetZoneText()` | [link](https://wowpedia.fandom.com/wiki/GetZoneText) | `UpdatePlayerState` |
| `GetSubZoneText()` | [link](https://wowpedia.fandom.com/wiki/GetSubZoneText) | `UpdatePlayerState` |
| `IsInInstance()` | [link](https://wowpedia.fandom.com/wiki/IsInInstance) | `UpdatePlayerState` |
| `IsMounted()` | [link](https://wowpedia.fandom.com/wiki/IsMounted) | `GetCurrentCompanion` |
| `GetTime()` | [link](https://wowpedia.fandom.com/wiki/GetTime) | `PushEvent`, `UpdatePlayerState` |

---

## Group & Social APIs

| API | Wowpedia | Used In |
|---|---|---|
| `GetNumGroupMembers()` | [link](https://wowpedia.fandom.com/wiki/GetNumGroupMembers) | `UpdateSocialState` |
| `HasPetSpells()` | [link](https://wowpedia.fandom.com/wiki/HasPetSpells) | `GetCurrentCompanion` |

---

## Namespace APIs (C_*)

| API | Wowpedia | Used In |
|---|---|---|
| `C_Timer.NewTicker(interval, fn)` | [link](https://wowpedia.fandom.com/wiki/C_Timer.NewTicker) | `frame OnEvent PLAYER_LOGIN` |
| `C_NamePlate.GetNamePlates()` | [link](https://wowpedia.fandom.com/wiki/C_NamePlate.GetNamePlates) | `UpdateSocialState` |
| `C_MountJournal.GetMountFromSpell(spellId)` | [link](https://wowpedia.fandom.com/wiki/C_MountJournal.GetMountFromSpell) | `GetCurrentCompanion` |
| `C_PetJournal.GetSummonedPetGUID()` | [link](https://wowpedia.fandom.com/wiki/C_PetJournal.GetSummonedPetGUID) | `GetCurrentCompanion` |
| `C_PetJournal.GetPetInfoByPetID(guid)` | [link](https://wowpedia.fandom.com/wiki/C_PetJournal.GetPetInfoByPetID) | `GetCurrentCompanion` |
| `C_PetJournal.GetPetInfoBySpeciesID(id)` | [link](https://wowpedia.fandom.com/wiki/C_PetJournal.GetPetInfoBySpeciesID) | `GetCurrentCompanion` |

---

## Frame / Widget APIs

| API | Wowpedia | Used In |
|---|---|---|
| `CreateFrame("EditBox", ...)` | [link](https://wowpedia.fandom.com/wiki/CreateFrame) | State EditBox (`MantellaWoW_State`) |
| `CreateFrame("Frame")` | [link](https://wowpedia.fandom.com/wiki/CreateFrame) | Event listener frames |
| `frame:RegisterEvent(event)` | [link](https://wowpedia.fandom.com/wiki/Frame:RegisterEvent) | All event frames |
| `frame:SetScript("OnEvent", fn)` | [link](https://wowpedia.fandom.com/wiki/Frame:SetScript) | All event frames |
| `editbox:SetText(str)` | [link](https://wowpedia.fandom.com/wiki/EditBox:SetText) | `OnUpdate` (state export) |

---

## ⚠️ Known Issues / Deprecation Watch

| API | Status | Notes |
|---|---|---|
| `UnitAura("player", i)` | ⚠️ Changed in 10.1 | Consider migrating to `C_UnitAuras.GetAuraDataByIndex()` — see [Wowpedia](https://wowpedia.fandom.com/wiki/C_UnitAuras.GetAuraDataByIndex) |
| `UnitHealthPercent` with `CurveConstants` | ⚠️ Verify | `CurveConstants.ScaleTo100` — confirm this constant exists in current API |
| `UnitIsDead` | ✅ Valid | Prefer over `UnitIsDeadOrGhost` for pets |
