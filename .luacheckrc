-- .luacheckrc
-- Luacheck configuration for WoW addon development

std = "lua51"
max_line_length = 120
codes = true

-- WoW API globals
globals = {
    "UnitName", "UnitLevel", "UnitClass", "UnitHealth", "UnitHealthMax",
    "UnitHealthPercent", "UnitCreatureFamily", "UnitCreatureType",
    "UnitIsDead", "UnitIsDeadOrGhost", "UnitExists", "UnitAffectingCombat",
    "GetZoneText", "GetSubZoneText", "IsInInstance", "HasPetSpells",
    "IsMounted", "UnitAura", "C_PetJournal", "C_MountJournal",
    "C_Timer", "CreateFrame", "SendChatMessage", "CopyToClipboard",
    "GetTime", "UIParent", "DEFAULT_CHAT_FRAME", "print", "message",
    "tostring", "tonumber", "pcall", "pairs", "ipairs", "table", "math",
    "string", "select", "type", "QuestieDB", "QuestiePlayer", "DBM",
    "CurveConstants", "MantellaWoWDB", "GetNumGroupMembers", "C_NamePlate",
    "UnitIsPlayer", "UnitReaction"
}

-- Ignore whitespace issues
ignore = {
    "611"
}

-- Unused arguments are common in WoW event handlers
unused_args = false

-- Unused variables are common for forward declarations
unused = false
