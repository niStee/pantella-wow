# Pantella WoW Addon

World of Warcraft integration for Pantella.

## Installation

1. Clone or download this repository.
2. Install addon requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the `MantellaWoW` addon folder into your WoW `Interface/AddOns/` directory.
4. In Pantella, select the WoW game interface and load the `wow` config.

## Requirements

- `pywin32>=306`
- `watchdog>=3.0`
- Windows OS (for EditBox scraping)
