# Pantella WoW Addon

World of Warcraft integration for Pantella. Experience real-time radiant AI conversations with NPCs and your pets directly inside the game, triggered dynamically by your Combat Log and in-game events!

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
