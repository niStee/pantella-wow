-- MantellaWoW: Ultimate Immersion Update
-- Pet Integration + EditBox State Export

local addonName, addon = ...

local defaults = {
    version = "3.0.0",
    player_name = "",
    player_level = 0,
    player_class = "",
    zone = "",
    subzone = "",
    in_combat = false,
    is_in_instance = false,
    active_quests = {},
    dbm_timers = {},
    combat_events = {},
    timestamp = 0,
    -- Pet data
    pet = {
        name = "Companion",
        family = "Unknown",
        type = "Unknown",
        health = 100,
        is_dead = false,
        is_attacking = false,
        target = nil
    },
    companion_name = "Companion",
    companion_type = "Unknown"
}

-- Simple JSON encoder
local function ToJSON(obj)
    local t = type(obj)
    if t == "string" then return string.format("%q", obj)
    elseif t == "number" then return tostring(obj)
    elseif t == "boolean" then return obj and "true" or "false"
    elseif t == "table" then
        local parts = {}
        for k, v in pairs(obj) do
            table.insert(parts, string.format("%s:%s", ToJSON(k), ToJSON(v)))
        end
        return "{" .. table.concat(parts, ",") .. "}"
    end
    return "null"
end

local function InitializeAddon()
    if not MantellaWoWDB then
        MantellaWoWDB = defaults
    end
    for k, v in pairs(defaults) do
        if MantellaWoWDB[k] == nil then
            MantellaWoWDB[k] = v
        end
    end
end

-- Pet detection
local function GetPetInfo()
    if not UnitExists("pet") then
        return nil
    end
    
    local health = 0
    if UnitHealthMax("pet") > 0 then
        health = math.floor((UnitHealth("pet") / UnitHealthMax("pet")) * 100)
    end
    
    return {
        name = UnitName("pet") or "Companion",
        family = UnitCreatureFamily("pet") or "Unknown",
        type = UnitCreatureType("pet") or "Unknown",
        health = health,
        is_dead = UnitIsDead("pet") or false,
        is_attacking = UnitAffectingCombat("pet") or false,
        target = UnitName("pettarget") or nil
    }
end

-- Hidden EditBox for state export
local stateFrame = CreateFrame("EditBox", "MantellaWoW_State", UIParent)
stateFrame:Hide()
stateFrame:SetMultiLine(false)
stateFrame:SetMaxLetters(0)
stateFrame:SetWidth(1)
stateFrame:SetHeight(1)
stateFrame:SetAutoFocus(false)
stateFrame:SetText("")

local function UpdatePlayerState()
    local db = MantellaWoWDB
    db.player_name = UnitName("player") or ""
    db.player_level = UnitLevel("player") or 0
    db.player_class = select(1, UnitClass("player")) or ""
    db.zone = GetZoneText() or ""
    db.subzone = GetSubZoneText() or ""
    db.in_combat = UnitAffectingCombat("player") or false
    db.is_in_instance = IsInInstance() or false
    db.timestamp = GetTime()
end

local function UpdateQuestState()
    local db = MantellaWoWDB
    db.active_quests = {}
    if QuestieDB and QuestiePlayer and QuestiePlayer.currentQuestlog then
        for questId, _ in pairs(QuestiePlayer.currentQuestlog) do
            local quest = QuestieDB.GetQuest(questId)
            if quest then
                table.insert(db.active_quests, {
                    id = questId,
                    name = quest.name or "Unknown",
                    level = quest.questLevel or 0,
                    completed = quest.isComplete or false
                })
            end
        end
    end
end

local function UpdateDBMState()
    local db = MantellaWoWDB
    db.dbm_timers = {}
    if DBM and DBM.TimerTracker then
        for _, timer in pairs(DBM.TimerTracker) do
            if timer and timer.id and timer.timer then
                table.insert(db.dbm_timers, {
                    id = timer.id,
                    time_remaining = timer.timer,
                    message = timer.msg or "",
                    spell_id = timer.spellId or 0
                })
            end
        end
    end
end

local function UpdatePetState()
    local db = MantellaWoWDB
    local pet = GetPetInfo()
    
    if pet then
        db.pet = pet
        db.companion_name = pet.name
        db.companion_type = pet.family
    else
        db.pet = { name = "Companion", family = "Unknown", type = "Unknown", health = 100, is_dead = false, is_attacking = false, target = nil }
        db.companion_name = "Companion"
        db.companion_type = "Unknown"
    end
end

local function OnUpdate()
    UpdatePlayerState()
    UpdateQuestState()
    UpdateDBMState()
    UpdatePetState()
    
    local json = ToJSON(MantellaWoWDB)
    stateFrame:SetText(json)
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("ADDON_LOADED")
frame:RegisterEvent("PLAYER_LOGIN")
frame:RegisterEvent("PLAYER_LOGOUT")

frame:SetScript("OnEvent", function(self, event, arg1)
    if event == "ADDON_LOADED" and arg1 == addonName then
        InitializeAddon()
    elseif event == "PLAYER_LOGIN" then
        C_Timer.NewTicker(1.0, OnUpdate)
    elseif event == "PLAYER_LOGOUT" then
        OnUpdate()
    end
end)

print("|cff00ff00[MantellaWoW]|r Loaded v" .. defaults.version)
