-- MantellaWoW: AI Companion Bridge for Pantella
-- Reads game state from Questie, DBM, and Details! and dumps to SavedVariables

local addonName, addon = ...
local M = {}

-- Default database structure
local defaults = {
    player_name = "",
    player_level = 0,
    player_class = "",
    zone = "",
    subzone = "",
    in_combat = false,
    is_in_instance = false,
    active_quests = {},
    quest_objectives = {},
    dbm_timers = {},
    recent_deaths = 0,
    last_encounter = "",
    dps = 0,
    hps = 0,
    timestamp = 0,
    version = "1.0.0"
}

-- Initialize addon
local function InitializeAddon()
    if not MantellaWoWDB then
        MantellaWoWDB = defaults
    end

    -- Ensure all default keys exist
    for key, value in pairs(defaults) do
        if MantellaWoWDB[key] == nil then
            MantellaWoWDB[key] = value
        end
    end

    print("|cff00ff00[MantellaWoW]|r Initialized. Waiting for dependencies...")
end

-- Update player state
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

-- Update quest state from Questie
local function UpdateQuestState()
    local db = MantellaWoWDB
    db.active_quests = {}
    db.quest_objectives = {}

    -- Check if Questie is available
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

                -- Get objectives
                if quest.Objectives then
                    db.quest_objectives[questId] = {}
                    for _, obj in pairs(quest.Objectives) do
                        table.insert(db.quest_objectives[questId], {
                            text = obj.text or "",
                            completed = obj.completed or false
                        })
                    end
                end
            end
        end
    end
end

-- Update DBM timers
local function UpdateDBMState()
    local db = MantellaWoWDB
    db.dbm_timers = {}

    -- Check if DBM is available
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

-- Update Details! combat data
local function UpdateDetailsState()
    local db = MantellaWoWDB

    -- Check if Details! is available
    if Details and Details.GetEncounter then
        local encounter = Details:GetEncounter()
        if encounter then
            db.last_encounter = encounter.name or ""
            db.recent_deaths = encounter.deaths or 0

            -- Get DPS/HPS if available
            local player = Details:GetPlayer("player")
            if player then
                db.dps = player.dps or 0
                db.hps = player.hps or 0
            end
        end
    end
end

local function ToJSON(val)
    local t = type(val)
    if t == "string" then
        return '"' .. val:gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('\n', '\\n') .. '"'
    elseif t == "number" or t == "boolean" then
        return tostring(val)
    elseif t == "table" then
        local isArray = false
        if next(val) == nil or val[1] ~= nil then
            isArray = true
        end
        local res = {}
        if isArray then
            for _, v in ipairs(val) do
                table.insert(res, ToJSON(v))
            end
            return "[" .. table.concat(res, ",") .. "]"
        else
            for k, v in pairs(val) do
                table.insert(res, '"' .. tostring(k) .. '":' .. ToJSON(v))
            end
            return "{" .. table.concat(res, ",") .. "}"
        end
    else
        return "null"
    end
end

-- Main update loop
local function OnUpdate()
    UpdatePlayerState()
    UpdateQuestState()
    UpdateDBMState()
    UpdateDetailsState()

    -- Write to clipboard
    local stateStr = "MANTELLA:" .. ToJSON(MantellaWoWDB)
    if CopyToClipboard then
        CopyToClipboard(stateStr)
    end
end

-- Event frame
local frame = CreateFrame("Frame")
frame:RegisterEvent("ADDON_LOADED")
frame:RegisterEvent("PLAYER_LOGIN")
frame:RegisterEvent("PLAYER_LOGOUT")

frame:SetScript("OnEvent", function(self, event, arg1)
    if event == "ADDON_LOADED" and arg1 == addonName then
        InitializeAddon()
    elseif event == "PLAYER_LOGIN" then
        print("|cff00ff00[MantellaWoW]|r Player logged in. Starting state tracking...")

        -- Start polling loop (1 second intervals)
        C_Timer.NewTicker(1.0, OnUpdate)
    elseif event == "PLAYER_LOGOUT" then
        -- Final state update before logout
        OnUpdate()
        print("|cff00ff00[MantellaWoW]|r Saving final state...")
    end
end)

print("|cff00ff00[MantellaWoW]|r Addon loaded. Version " .. defaults.version)
