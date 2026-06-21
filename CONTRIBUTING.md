# Contributing to pantella-wow

Thank you for contributing! Please read this guide before opening a PR.

---

## The Golden Rule: No Unverified API Assumptions

> **If you can't link it, don't ship it.**

Every WoW API call, event name, pet family spec, or third-party addon schema must be
verified against a canonical source **before** it enters the codebase.

---

## Source of Truth Hierarchy

Use sources in this order — highest authority first:

### Tier 1a — In-game Blizzard API (always current)
- **In-game**: `/api` → `Blizzard_APIDocumentation` addon
- No internet needed. Works offline. Always reflects the exact game version running.
- Use this to confirm parameter counts, return values, and event payload structure.

### Tier 1b — Blizzard Developer Portal (canonical for post-10.1.7 APIs)
- **URL**: https://develop.battle.net/documentation/world-of-warcraft
- Use this for:
  - Lua APIs **added or changed after patch 10.1.7 (August 2023)**
  - REST API calls (character data, realm status, auction house)
  - OAuth 2.0 flows
  - Any case where Wowpedia says "needs updating" or shows outdated parameters
- Code comment format:
  ```python
  # Blizzard Dev Portal: https://develop.battle.net/documentation/world-of-warcraft
  # (Wowpedia outdated for this API)
  ```

### Tier 1c — Townlong Yak FrameXML (live viewer)
- **URL**: https://www.townlong-yak.com/framexml/live
- Use this for: reading live FrameXML/Lua source for any API or event not well-documented elsewhere.

### Tier 2 — Wowpedia (good for stable pre-10.1.7 APIs and lore)
- https://wowpedia.fandom.com/wiki/World_of_Warcraft_API
- https://wowpedia.fandom.com/wiki/Events
- ✅ Reliable for: events/APIs unchanged since Classic (`ZONE_CHANGED_NEW_AREA`, `UnitHealth`, etc.)
- ⚠️ **Partially frozen after patch 10.1.7 (August 2023)** — use Tier 1b for newer APIs
- ✅ Reliable for: lore, pet families, pet specs, minion abilities
- Code comment format:
  ```python
  # Wowpedia: https://wowpedia.fandom.com/wiki/ZONE_CHANGED_NEW_AREA
  ```

### Tier 3 — Third-party addon GitHub sources
- **BigWigs** (recommended): https://github.com/BigWigsMods/BigWigs
  - Schema: `BigWigs_StartBar(module, id, text, duration, icon)` — verified from [Bars.lua](https://github.com/BigWigsMods/BigWigs/blob/master/Plugins/Bars.lua)
- **DBM**: https://github.com/DeadlyBossMods/DBM-Retail
  - Callback reference: https://github.com/WeakAuras/WeakAuras2
- Do **not** use Wowpedia or the Blizzard Dev Portal for third-party addon APIs — they don't cover them.

---

## Required Practices

### For every new WoW Lua event or API in Python:

If Wowpedia is current (pre-10.1.7 API):
```python
# Wowpedia: https://wowpedia.fandom.com/wiki/ZONE_CHANGED_NEW_AREA
if etype == 'zone':
    ...
```

If the API is post-10.1.7 or Wowpedia is outdated:
```python
# Blizzard Dev Portal: https://develop.battle.net/documentation/world-of-warcraft
# Wowpedia: https://wowpedia.fandom.com/wiki/SOME_EVENT  (outdated — Dev Portal is primary)
if etype == 'some_event':
    ...
```

- Comment must appear **within 6 lines above** the first usage
- Add an entry to `docs/API_ASSUMPTIONS.md` (include Dev Portal column)
- Add an entry to `docs/LUA_EVENT_REFERENCE.md`
- **Enforced by** `tests/test_api_assumptions.py`

### For every new WoW Lua event in the Lua addon (`MantellaWoW.lua`):
```lua
-- Wowpedia: https://wowpedia.fandom.com/wiki/ZONE_CHANGED_NEW_AREA
frame:RegisterEvent("ZONE_CHANGED_NEW_AREA")
```
For post-10.1.7 events:
```lua
-- Blizzard Dev Portal: https://develop.battle.net/documentation/world-of-warcraft
frame:RegisterEvent("SOME_NEW_EVENT")
```

### For every new pet personality:
```python
# Wowpedia spec: Ferocity
# https://wowpedia.fandom.com/wiki/Cat_(hunter_pet)
'Cat': (
    'You are a Cat of Ferocity specialization...'
),
```
- Spec must be mentioned in the personality text
- Enforced by `TestHunterSpecCorrectness`
- Use `.github/ISSUE_TEMPLATE/add_pet.yml` as a checklist

### For new third-party addon schemas:
```python
# BigWigs_StartBar schema: (module, id, text, duration, icon)
# Source: https://github.com/BigWigsMods/BigWigs/blob/master/Plugins/Bars.lua
```
Comment must reference the **exact file**, not just the repo.

---

## What Gets a PR Rejected

| Violation | Test that catches it |
|---|---|
| WoW event used without source comment | `test_api_assumptions.py::TestLuaEventComments` |
| `develop.battle.net` not in CONTRIBUTING | `test_api_assumptions.py::TestBlizzardDevPortalDocumented` |
| Pet with wrong spec | `TestHunterSpecCorrectness` |
| Pet without Wowpedia comment | `TestWowpediaSourceOfTruth` |
| DBM tests un-skipped without Lua implementation | `TestDBMTimerTriggers` (skipped) |
| `docs/API_ASSUMPTIONS.md` missing BigWigs/DBM docs | `TestBigWigsSchemaDocumented` |
| `docs/LUA_EVENT_REFERENCE.md` missing event | `TestLuaEventReferenceDoc` |

---

## Running the Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Skipped tests (DBM) show as `s` — that's correct. All other tests must be **green**.

---

## Adding a Feature Checklist

- [ ] New Lua event/API? → Source comment (Wowpedia for pre-10.1.7, Dev Portal for newer) + `docs/API_ASSUMPTIONS.md` + `docs/LUA_EVENT_REFERENCE.md`
- [ ] Post-10.1.7 API? → `develop.battle.net` comment as primary, Wowpedia as secondary
- [ ] New pet/guardian/companion? → Wowpedia URL comment + spec in text + test in `TestHunterSpecCorrectness`
- [ ] New third-party addon schema? → GitHub source link to exact file + `@unittest.skip` until Lua implements it
- [ ] Tests green locally? (`pytest tests/ -v`)
- [ ] No new `# TODO` or `# FIXME` without a linked issue?
