-- MantellaWoW: Ultimate Immersion Update
-- Pet Integration + EditBox State Export

local addonName, addon = ...

local defaults = {
    version = "3.1.0",
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
    chattyness = 3,
    recent_events = {},
    nearby = { players = {}, npcs = {}, hostile = {} },
    group_size = 0,
    -- Pet data
    pet = {
        name = "Companion",
        family = "Unknown",
        type = "Unknown",
        health = 100,
        is_dead = false,
        is_attacking = false,
        target = nil,
        lore = ""
    },
    companion_name = "Companion",
    companion_type = "Unknown"
}

-- Simple JSON encoder (Optimized to skip empty arrays)
local function ToJSON(obj)
    local t = type(obj)
    if t == "string" then return string.format("%q", obj)
    elseif t == "number" then return tostring(obj)
    elseif t == "boolean" then return obj and "true" or "false"
    elseif t == "table" then
        local count = 0
        for _ in pairs(obj) do count = count + 1 end
        if count == 0 then return "{}" end
        
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

-- Event Ring Buffer
local EVENT_BUFFER_SIZE = 5
local event_buffer = {}
local event_counter = 0

local function PushEvent(event_type, data)
    event_counter = event_counter + 1
    local slot = ((event_counter - 1) % EVENT_BUFFER_SIZE) + 1
    event_buffer[slot] = {
        id = event_counter,
        type = event_type,
        data = data,
        time = GetTime()
    }
end

-- Pet detection
local function GetCurrentCompanion()
    if IsMounted() then
        local mountName = "Mount"
        for i = 1, 40 do
            local name, _, _, _, _, _, _, _, _, spellId = UnitAura("player", i)
            if name and spellId then
                local mountID = C_MountJournal.GetMountFromSpell(spellId)
                if mountID then
                    mountName = name
                    break
                end
            end
        end
        
        return {
            name = mountName,
            family = "Mount",
            type = "Mount",
            health = 100,
            is_dead = false,
            is_attacking = false,
            target = nil,
            pet_token = "MOUNT"
        }
    end
    
    local hasSpells, petToken = HasPetSpells()
    if hasSpells then
        local name = UnitName("pet")
        if name and name ~= "" then
            local creatureType = UnitCreatureType("pet") or "Unknown"
            local family = UnitCreatureFamily("pet") or "Unknown"
            if petToken == "DEMON" or family == "Unknown" then
                family = creatureType
            end
            
            local health = 100
            local isDead = UnitIsDead("pet") or false
            if not isDead then
                local success, result = pcall(function()
                    local pct = UnitHealthPercent("pet", true, CurveConstants.ScaleTo100)
                    if pct then return tonumber(string.format("%.0f", pct)) end
                    return 100
                end)
                if success and result then health = result end
            else
                health = 0
            end
            
            return {
                name = name,
                family = family,
                type = creatureType,
                health = health,
                is_dead = isDead,
                is_attacking = UnitAffectingCombat("pet") or false,
                target = UnitName("pettarget") or nil,
                pet_token = petToken
            }
        end
    end
    
    local petGUID = C_PetJournal.GetSummonedPetGUID()
    if petGUID then
        local speciesID, customName = C_PetJournal.GetPetInfoByPetID(petGUID)
        local name = customName
        local description = ""
        if speciesID then
            local speciesName, _, _, _, desc = C_PetJournal.GetPetInfoBySpeciesID(speciesID)
            if not name or name == "" then name = speciesName or "Companion" end
            description = desc or ""
        end
        
        if not name or name == "" then name = "Companion" end
        
        return {
            name = name,
            family = "Companion",
            type = "Companion",
            health = 100,
            is_dead = false,
            is_attacking = false,
            target = nil,
            pet_token = "COMPANION",
            lore = description
        }
    end
    
    return nil
end

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
    local newZone = GetZoneText() or ""
    if newZone ~= "" and db.zone ~= newZone then
        PushEvent("zone", newZone)
    end
    db.zone = newZone
    db.subzone = GetSubZoneText() or ""
    
    local in_combat = UnitAffectingCombat("player") or false
    if in_combat and not db.in_combat then
        PushEvent("combat", "Enter Combat")
    end
    db.in_combat = in_combat
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

local function UpdateSocialState()
    local db = MantellaWoWDB
    db.group_size = GetNumGroupMembers()
    db.nearby = { players = {}, npcs = {}, hostile = {} }
    
    local plates = C_NamePlate.GetNamePlates()
    for _, plate in ipairs(plates) do
        local unit = plate.namePlateUnitToken
        if unit then
            local name = UnitName(unit)
            if name then
                if UnitIsPlayer(unit) then
                    if #db.nearby.players < 3 then table.insert(db.nearby.players, name) end
                elseif UnitReaction("player", unit) and UnitReaction("player", unit) < 4 then
                    if #db.nearby.hostile < 3 then table.insert(db.nearby.hostile, name) end
                else
                    if #db.nearby.npcs < 3 then table.insert(db.nearby.npcs, name) end
                end
            end
        end
    end
end

-- Chat tracking
local chatFrame = CreateFrame("Frame")
chatFrame:RegisterEvent("CHAT_MSG_SAY")
chatFrame:RegisterEvent("CHAT_MSG_PARTY")
chatFrame:RegisterEvent("CHAT_MSG_WHISPER")
chatFrame:RegisterEvent("CHAT_MSG_EMOTE")

chatFrame:SetScript("OnEvent", function(self, event, msg, sender, ...)
    if sender == UnitName("player") then return end
    PushEvent("chat", sender .. ": " .. msg)
end)

-- NPC/Interaction tracking
local interactionFrame = CreateFrame("Frame")
interactionFrame:RegisterEvent("GOSSIP_SHOW")
interactionFrame:RegisterEvent("QUEST_ACCEPTED")
interactionFrame:RegisterEvent("QUEST_COMPLETE")
interactionFrame:RegisterEvent("TRADE_SHOW")
interactionFrame:RegisterEvent("MERCHANT_SHOW")

interactionFrame:SetScript("OnEvent", function(self, event, ...)
    local target = UnitName("npc") or "Unknown"
    if event == "TRADE_SHOW" then target = UnitName("target") or "Unknown" end
    PushEvent(event:lower(), target)
end)

local last_json = ""
local last_hash = ""

local function HashState()
    local pet = MantellaWoWDB.pet or {}
    return string.format("%s|%s|%s|%d|%s|%d",
        pet.name or "",
        pet.family or "",
        pet.health or 0,
        MantellaWoWDB.in_combat and 1 or 0,
        MantellaWoWDB.zone or "",
        event_counter
    )
end

local function OnUpdate()
    UpdatePlayerState()
    UpdateSocialState()
    UpdateQuestState()
    UpdateDBMState()
    
    local companion = GetCurrentCompanion()
    if companion then
        MantellaWoWDB.pet = companion
        MantellaWoWDB.companion_name = companion.name
        MantellaWoWDB.companion_type = companion.family
    else
        MantellaWoWDB.pet = {
            name = "Spirit", family = "Unknown", type = "Unknown",
            health = 100, is_dead = false, is_attacking = false
        }
        MantellaWoWDB.companion_name = "Spirit"
        MantellaWoWDB.companion_type = "Unknown"
    end
    
    -- Copy event buffer into state
    MantellaWoWDB.recent_events = {}
    for i = 1, EVENT_BUFFER_SIZE do
        if event_buffer[i] then
            table.insert(MantellaWoWDB.recent_events, event_buffer[i])
        end
    end
    
    local current_hash = HashState()
    if current_hash ~= last_hash then
        last_hash = current_hash
        local json = ToJSON(MantellaWoWDB)
        stateFrame:SetText(json)
        last_json = json
    end
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
