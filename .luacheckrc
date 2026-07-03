-- .luacheckrc
-- Luacheck configuration for WoW addon development
-- All globals validated against Wowpedia: https://wowpedia.fandom.com/wiki/Wowpedia
-- WoW version: 11.x (The War Within)
-- Last reviewed: 2026-06-22
--
-- Workflow: when adding a new WoW API global, add it here AND in
--   docs/wow_lua_api_used.md with its Wowpedia URL.

std = "lua51"
max_line_length = 120
codes = true

globals = {

    -- ── Unit APIs ────────────────────────────────────────────────────────
    -- https://wowpedia.fandom.com/wiki/UnitName
    "UnitName",
    -- https://wowpedia.fandom.com/wiki/UnitLevel
    "UnitLevel",
    -- https://wowpedia.fandom.com/wiki/UnitClass
    "UnitClass",
    -- https://wowpedia.fandom.com/wiki/UnitHealth
    "UnitHealth",
    -- https://wowpedia.fandom.com/wiki/UnitHealthMax
    "UnitHealthMax",
    -- https://wowpedia.fandom.com/wiki/UnitHealthPercent
    "UnitHealthPercent",
    -- https://wowpedia.fandom.com/wiki/UnitCreatureFamily
    "UnitCreatureFamily",
    -- https://wowpedia.fandom.com/wiki/UnitCreatureType
    "UnitCreatureType",
    -- https://wowpedia.fandom.com/wiki/UnitIsDead
    "UnitIsDead",
    -- https://wowpedia.fandom.com/wiki/UnitIsDeadOrGhost
    "UnitIsDeadOrGhost",
    -- https://wowpedia.fandom.com/wiki/UnitExists
    "UnitExists",
    -- https://wowpedia.fandom.com/wiki/UnitAffectingCombat
    "UnitAffectingCombat",
    -- https://wowpedia.fandom.com/wiki/UnitIsPlayer
    "UnitIsPlayer",
    -- https://wowpedia.fandom.com/wiki/UnitReaction
    "UnitReaction",
    -- https://wowpedia.fandom.com/wiki/UnitAura
    -- DEPRECATION WATCH: Changed in patch 10.1. Prefer C_UnitAuras.GetAuraDataByIndex.
    "UnitAura",

    -- ── Zone & World APIs ────────────────────────────────────────────────
    -- https://wowpedia.fandom.com/wiki/GetZoneText
    "GetZoneText",
    -- https://wowpedia.fandom.com/wiki/GetSubZoneText
    "GetSubZoneText",
    -- https://wowpedia.fandom.com/wiki/IsInInstance
    "IsInInstance",
    -- https://wowpedia.fandom.com/wiki/IsMounted
    "IsMounted",
    -- https://wowpedia.fandom.com/wiki/GetTime
    "GetTime",

    -- ── Group APIs ───────────────────────────────────────────────────────
    -- https://wowpedia.fandom.com/wiki/GetNumGroupMembers
    "GetNumGroupMembers",
    -- https://wowpedia.fandom.com/wiki/HasPetSpells
    "HasPetSpells",

    -- ── Namespace APIs (C_*) ─────────────────────────────────────────────
    -- https://wowpedia.fandom.com/wiki/C_Timer.NewTicker
    "C_Timer",
    -- https://wowpedia.fandom.com/wiki/C_NamePlate.GetNamePlates
    "C_NamePlate",
    -- https://wowpedia.fandom.com/wiki/C_MountJournal.GetMountFromSpell
    "C_MountJournal",
    -- https://wowpedia.fandom.com/wiki/C_PetJournal.GetSummonedPetGUID
    "C_PetJournal",
    -- https://wowpedia.fandom.com/wiki/C_UnitAuras.GetAuraDataByIndex
    -- Future migration target for UnitAura() calls.
    "C_UnitAuras",
    -- https://wowpedia.fandom.com/wiki/C_Map
    "C_Map",

    -- ── Frame & Widget APIs ──────────────────────────────────────────────
    -- https://wowpedia.fandom.com/wiki/CreateFrame
    "CreateFrame",
    -- https://wowpedia.fandom.com/wiki/UIParent
    "UIParent",

    -- ── Chat APIs ────────────────────────────────────────────────────────
    -- https://wowpedia.fandom.com/wiki/SendChatMessage
    "SendChatMessage",
    -- https://wowpedia.fandom.com/wiki/DEFAULT_CHAT_FRAME
    "DEFAULT_CHAT_FRAME",
    -- https://wowpedia.fandom.com/wiki/CopyToClipboard
    "CopyToClipboard",

    -- ── WoW Constants ────────────────────────────────────────────────────
    -- DEPRECATION WATCH: Verify CurveConstants.ScaleTo100 still valid in current patch.
    -- https://wowpedia.fandom.com/wiki/UnitHealthPercent
    "CurveConstants",

    -- ── Third-Party Addon APIs ────────────────────────────────────────────
    -- Questie quest database (optional dependency)
    "QuestieDB",
    "QuestiePlayer",
    -- Deadly Boss Mods timer tracker (optional dependency)
    "DBM",

    -- ── Addon SavedVariables ─────────────────────────────────────────────
    -- Declared in MantellaWoW.toc as ## SavedVariables: MantellaWoWDB
    "MantellaWoWDB",

    -- ── Lua 5.1 std overrides ─────────────────────────────────────────────
    -- These are already in std=lua51 but listed explicitly for clarity
    "print", "message", "tostring", "tonumber", "pcall",
    "pairs", "ipairs", "table", "math", "string", "select", "type",
}

-- Ignore whitespace issues
ignore = {
    "611",  -- whitespace before colon
}

-- Unused arguments are common in WoW event handlers (self, event, ...)
unused_args = false

-- Unused variables are common for forward declarations in Lua
unused = false
