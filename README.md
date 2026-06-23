# Pantella WoW Addon

[![CI](https://github.com/niStee/pantella-wow/actions/workflows/ci.yml/badge.svg)](https://github.com/niStee/pantella-wow/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/niStee/pantella-wow/badge)](https://securityscorecards.dev/viewer/?uri=github.com/niStee/pantella-wow)
[![CodeQL](https://github.com/niStee/pantella-wow/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/niStee/pantella-wow/security/code-scanning)
[![Dependency Graph](https://github.com/niStee/pantella-wow/actions/workflows/dependabot/update-graph/badge.svg)](https://github.com/niStee/pantella-wow/network/dependencies)


World of Warcraft integration for [Pantella](https://github.com/Pathos14489/Pantella) (a powerful LLM-bridge for gaming), inspired by the original [Mantella](https://github.com/art-from-the-machine/Mantella) project. 

Experience real-time radiant AI conversations with NPCs and your pets directly inside the game, triggered dynamically by your Combat Log and in-game events!

## Installation

1. Clone or download this repository.
2. Install addon requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the `MantellaWoW` addon folder into your WoW `Interface/AddOns/` directory.
4. In Pantella, select the WoW game interface and load the `wow` config.

## Features

- **Real-time Combat Log Integration**: Triggers radiant conversations based on in-game events (combat, taking damage, killing mobs).
- **In-Game Overlay UI**: A transparent, always-on-top Tkinter overlay that displays what your pets and NPCs are saying directly on your screen without tabbing out.
- **Pet Personality**: Dynamic prompt injection based on your WoW Pet's active family (e.g., Cat, Bear, Raptor).

## Requirements

- `pywin32>=306`
- `watchdog>=3.0`
- Windows OS (for EditBox scraping and transparent Overlay UI)

## Development

When adding or updating dependencies, **do not** edit `requirements.txt` or `requirements-dev.txt` manually. We use `uv` and `pip-tools` for securely hashed dependencies to comply with OpenSSF Scorecard requirements.

1. Add your dependency to `requirements.in` (for runtime) or `requirements-dev.in` (for testing/CI).
2. Generate the locked hash files:
   ```bash
   uv pip compile --generate-hashes requirements.in -o requirements.txt
   uv pip compile --generate-hashes requirements-dev.in -o requirements-dev.txt
   ```

## Linting

Python code is linted with [ruff](https://docs.astral.sh/ruff/) (E, F, I, UP, B, SIM rules). Lua is linted with `luacheck`. Type checking via `mypy`.

```bash
ruff check game_interfaces/ tools/ tests/
ruff format --check game_interfaces/ tools/ tests/
```

## TDI: Test-Driven Infrastructure

This repo follows the Test-Driven Infrastructure methodology:

| Layer | Tool | What It Catches |
|-------|------|-----------------|
| Static Analysis | ruff (pyproject.toml), luacheck | Python/Lua syntax |
| Unit | pytest (3.10 + 3.11 matrix) | Component behavior |
| Contract | mypy | Type correctness |
| Compliance | GitHub Actions, Scorecard | Secrets, supply chain |
| E2E | GitHub Actions CI | Full lint + test + typecheck |

### Definition of Done
- [ ] `ruff check . && ruff format --check .` passes
- [ ] `luacheck MantellaWoW/` passes
- [ ] `mypy game_interfaces/` passes
- [ ] `pytest -v tests/` passes (Python 3.10 + 3.11)
- [ ] No secrets committed
