# AGENTS.md — pantella-wow

> Parent: [~/Projects/AGENTS.md](../AGENTS.md) — project index.

World of Warcraft integration for Pantella (LLM-bridge for gaming). Python backend with a Lua WoW addon. Radiant NPC/pet conversations triggered by combat-log events.

## Commands

| Action | Command |
|--------|---------|
| **Install deps** | `pip install -r requirements.txt` |
| **Install dev deps** | `pip install -r requirements-dev.txt` |
| **Run tests** | `pytest tests/ -v` |
| **Lint** | `ruff check . && ruff format --check .` |
| **Run overlay** | `python overlay.py` |

## Conventions

- Python 3.10+ target (`pyproject.toml`).
- Lint/format via `ruff` (line-length 100).
- Every new WoW Lua event or API must have a source comment (Wowpedia or Blizzard Dev Portal). See `CONTRIBUTING.md`.
- Pet personalities must include Wowpedia-verified spec (Ferocity/Tenacity/Cunning).
- Lua addon lives in `MantellaWoW/` — copy to WoW `Interface/AddOns/`.
- Git identity: `niStee` / `52573120+niStee@users.noreply.github.com`.
- Feature branches + PRs to `main`. CI runs pytest + ruff.

## Key Directories

| Path | Purpose |
|------|---------|
| `MantellaWoW/` | WoW Lua addon (FrameXML, event handlers) |
| `game_interfaces/` | Python game interface implementations |
| `character_db/` | NPC/pet character databases |
| `character_generators/` | Dynamic character prompt generators |
| `conversation_managers/` | Conversation state machines |
| `tests/` | pytest test suite |
| `docs/` | ADRs and architecture notes |

## Anti-Patterns

- Never hardcode WoW API version assumptions — verify against Blizzard Dev Portal.
- Never commit game client paths or user-specific WoW directories.
- Never skip Wowpedia/Dev Portal source comments on new events (enforced by tests).
