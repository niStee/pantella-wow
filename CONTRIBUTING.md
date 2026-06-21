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
- ✅ Reliable for: events/APIs unchanged since Classic (ZONE_CHANGED, UnitHealth, etc.)
- ⚠️ Partially frozen after patch **10.1.7 (August 2023)** — verify newer APIs elsewhere
- ✅ Reliable for: lore, pet families, pet specs, minion abilities

### 3. Third-party addon APIs (must use addon's own source)
- **DBM timers**: https://github.com/DeadlyBossMods/DBM-Retail
- **WeakAuras DBM integration** (best callback reference): https://github.com/WeakAuras/WeakAuras2
- **BigWigs**: https://github.com/BigWigsMods/BigWigs
- Do **not** use Wowpedia for third-party addon APIs.

---

## Required Practices

### For every new WoW API or event used:
```python
# Wowpedia: https://wowpedia.fandom.com/wiki/ZONE_CHANGED_NEW_AREA
if etype == 'zone':
    ...
```
Add the source URL as an inline comment **immediately above** the usage.
Update `docs/API_ASSUMPTIONS.md` with verification status.

### For every new pet personality added:
```python
# Wowpedia spec: Ferocity
# https://wowpedia.fandom.com/wiki/Cat_(hunter_pet)
'Cat': (
    'You are a Cat of Ferocity specialization...'
),
```
- Spec must be mentioned in the personality text (e.g. `Ferocity`, `Tenacity`, `Cunning`)
- Enforced by `TestHunterSpecCorrectness` — your test will be red if spec is wrong
- Use `.github/ISSUE_TEMPLATE/add_pet.yml` as a checklist

### For unimplemented / unverified features:
- Use `@unittest.skip("reason + tracking issue + real API reference")` on tests
- Do **not** leave tests green against a placeholder schema
- Add an entry to `docs/API_ASSUMPTIONS.md` with status `⚠️ Placeholder` or `❌ Wrong`

---

## What Gets a PR Rejected

- ❌ New WoW API/event used without a source comment
- ❌ Pet personality with wrong spec (fails `TestHunterSpecCorrectness`)
- ❌ DBM tests un-skipped without actual Lua addon implementation
- ❌ Any schema described as "the real API" without a verifiable source
- ❌ Wowpedia used as source for DBM, WeakAuras, or other third-party addon APIs

---

## Running the Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Skipped tests are expected (DBM) and will show as `s` in the output — that's correct.
All other tests must be green before a PR is ready for review.

---

## Adding a Feature Checklist

- [ ] New API/event? → Source comment + `docs/API_ASSUMPTIONS.md` entry
- [ ] New pet/guardian/companion? → Wowpedia URL comment + spec in text + test
- [ ] New third-party addon schema? → Link to addon source + `@unittest.skip` until implemented in Lua
- [ ] Tests green locally? (`pytest tests/ -v`)
- [ ] No new `# TODO` or `# FIXME` without a linked issue?
