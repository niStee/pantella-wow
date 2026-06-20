# WoW AI Companion Bridge (Pantella Fork)

## Architecture Overview
This project builds a real-time LLM companion for World of Warcraft.
- **Delivery**: Desktop Audio via Python (Option 1A) - easiest and most reliable path.
- **Scope**: Both Lorekeeper (Quests) and Tactician (Combat/DBM) (Option 2C).

## Component 1: Pantella Python Middleware (Fork)
We will fork Pantella and add a `wow.py` game interface to poll our local state file.

### Tasks
- [x] **Task 1 - Fork & Setup**: Fork `Pathos14489/Pantella` and clone it locally.
- [x] **Task 2 - Create Interface**: Create `src/game_interfaces/wow.py` inheriting from `BaseGameInterface`.
  - Implement `load_game_state()` to read `WTF/Account/<NAME>/SavedVariables/MantellaWoW.lua`.
  - Implement Lua-to-Python parser (e.g., regex or `slpp` module) to parse the `SavedVariables`.
  - Map WoW data to Pantella's internal state (player location, active quests, recent combat events).
- [x] **Task 3 - Configuration**: Create `config_presets/wow.json` to register the new interface.

## Component 2: MantellaWoW Lua Addon (New)
A clean-room WoW addon that extracts game state and dumps it to disk.

### Tasks
- [x] **Task 4 - Addon Skeleton**: Create `MantellaWoW.toc` and `MantellaWoW.lua`. Register `MantellaWoWDB` as a `SavedVariable`.
- [x] **Task 5 - Core API Hooks**:
  - `C_Timer.NewTicker`: Set a 1-2 second polling loop to update the `MantellaWoWDB` table.
  - Player State: `UnitName()`, `UnitLevel()`, `GetZoneText()`, `UnitAffectingCombat()`.
- [x] **Task 6 - Questie Integration (Lorekeeper)**:
  - Check if `QuestieDB` and `QuestiePlayer` are loaded.
  - Iterate active quests, extracting name, level, and objective progress.
- [x] **Task 7 - DBM / Details! Integration (Tactician)**:
  - Hook DBM's timer table to extract upcoming boss abilities.
  - Read Details! recent encounter summary (deaths, DPS, interrupts).
- [x] **Task 8 - Persistence**: Ensure the table structure is flat and clean so the Python parser can read it easily.

## Final Verification Wave
- [ ] **Task 9 - Verify Python adapter safely handles WoW file-locking** (if the file is being written while Python reads).
- [ ] **Task 10 - Verify TTS audio routes correctly** to the default system audio device without interrupting WoW.
- [ ] **Task 11 - Verify the LLM prompt correctly interprets** both Quest and Combat data seamlessly.
