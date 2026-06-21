# Contributing to pantella-wow

Thank you for contributing! Please read this guide before opening a PR.

---

## The Golden Rule: No Unverified API Assumptions

> **If you can't link it, don't ship it.**

Every WoW API call, event name, pet family spec, or third-party addon schema must be
verified against a canonical source **before** it enters the codebase.

This project has been burned by hallucinated API assumptions before (e.g. wrong Hunter pet
specializations, unimplemented DBM timer schema). We enforce verification via tests and
code comments.

---

## Source of Truth Hierarchy

Use sources in this order — highest authority first:

### 1. Blizzard WoW API (highest authority)
- **In-game**: `/api` → `Blizzard_APIDocumentation` (always current)
- **Live FrameXML viewer**: https://www.townlong-yak.com/framexml/live
- **Developer portal**: https://develop.battle.net/documentation/world-of-warcraft

### 2. Wowpedia (good for stable APIs and lore)
- https://wowpedia.fandom.com/wiki/World_of_Warcraft_API
- https://wowpedia.fandom.com/wiki/Events
- ✅ Reliable for: events/APIs unchanged since Classic (`ZONE_CHANGED_NEW_AREA`, `UnitHealth`, etc.)
- ⚠️ **Partially frozen after patch 10.1.7 (August 2023)** — verify newer APIs via Townlong Yak
- ✅ Reliable for: lore, pet families, pet specs, minion abilities

### 3. Third-party addon APIs (must use addon's own GitHub source)
- **BigWigs** (recommended): https://github.com/BigWigsMods/BigWigs
  - Schema: `BigWigs_StartBar(module, id, text, duration, icon)` — verified from [Bars.lua](https://github.com/BigWigsMods/BigWigs/blob/master/Plugins/Bars.lua)
- **DBM timers**: https://github.com/DeadlyBossMods/DBM-Retail
  - Callback reference: https://github.com/WeakAuras/WeakAuras2 (best available DBM schema doc)
- **WeakAuras**: https://github.com/WeakAuras/WeakAuras2
- Do **not** use Wowpedia for third-party addon APIs — it does not cover them.

---

## Required Practices

### For every new WoW Lua event or API used in Python:
```python
# Wowpedia: https://wowpedia.fandom.com/wiki/ZONE_CHANGED_NEW_AREA
if etype == 'zone':
    ...
```
- Add the source URL as an inline comment **within 6 lines above** the first usage
- Add an entry to `docs/API_ASSUMPTIONS.md`
- Add an entry to `docs/LUA_EVENT_REFERENCE.md`
- Enforced by `tests/test_api_assumptions.py` — tests will be **red** if comments are missing

### For every new WoW Lua event used in the Lua addon (`MantellaWoW.lua`):
```lua
-- Wowpedia: https://wowpedia.fandom.com/wiki/ZONE_CHANGED_NEW_AREA
frame:RegisterEvent("ZONE_CHANGED_NEW_AREA")
```
Same rule: URL comment within 3 lines above `RegisterEvent`.

### For every new pet personality added:
```python
# Wowpedia spec: Ferocity
# https://wowpedia.fandom.com/wiki/Cat_(hunter_pet)
'Cat': (
    'You are a Cat of Ferocity specialization...'
),
```
- Spec must be mentioned in the personality text
- Enforced by `TestHunterSpecCorrectness` in `tests/test_wow_personalities.py`
- Use `.github/ISSUE_TEMPLATE/add_pet.yml` as a checklist

### For new third-party addon schemas (BigWigs, DBM, etc.):
```python
# BigWigs_StartBar schema: (module, id, text, duration, icon)
# Source: https://github.com/BigWigsMods/BigWigs/blob/master/Plugins/Bars.lua
```
- Comment must reference the **exact file** in the addon's GitHub, not just the repo
- Add to `docs/API_ASSUMPTIONS.md` under the relevant addon section

### For unimplemented / unverified features:
- Use `@unittest.skip("reason + real API reference + tracking issue")` on tests
- Do **not** leave tests green against a placeholder schema
- Mark as `⚠️ Placeholder` or `❌ Wrong` in `docs/API_ASSUMPTIONS.md`

---

## What Gets a PR Rejected

| Violation | Test that catches it |
|---|---|
| WoW event used without Wowpedia URL comment | `test_api_assumptions.py` |
| Pet with wrong spec | `TestHunterSpecCorrectness` |
| Pet without Wowpedia comment | `TestWowpediaSourceOfTruth` |
| DBM tests un-skipped without Lua implementation | `TestDBMTimerTriggers` (skipped) |
| `docs/API_ASSUMPTIONS.md` missing BigWigs/DBM docs | `TestBigWigsSchemaDocumented` |
| `CONTRIBUTING.md` missing source tier | `TestContributingGuideCompleteness` |
| `docs/LUA_EVENT_REFERENCE.md` missing event | `TestLuaEventReferenceDoc` |

---

## Running the Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Skipped tests are expected (DBM) and show as `s` — that's correct.
All other tests must be **green** before a PR is ready.

---

## Adding a Feature Checklist

- [ ] New Lua event/API? → Wowpedia URL comment + `docs/API_ASSUMPTIONS.md` + `docs/LUA_EVENT_REFERENCE.md`
- [ ] New pet/guardian/companion? → Wowpedia URL comment + spec in text + test in `TestHunterSpecCorrectness`
- [ ] New third-party addon schema? → GitHub source link to exact file + `@unittest.skip` until Lua implements it
- [ ] Tests green locally? (`pytest tests/ -v`)
- [ ] No new `# TODO` or `# FIXME` without a linked issue?
