# Release Process

## What gets released

A single zip — `pantella-wow-vX.Y.Z.zip` — containing everything the user needs:

```
pantella-wow-v1.0.0.zip
├── MantellaWoW/           → copy to WoW/Interface/AddOns/
│   ├── MantellaWoW.lua
│   └── MantellaWoW.toc
├── game_interfaces/
│   └── wow.py             → copy to <Pantella>/game_interfaces/
├── interface_configs/     → copy to <Pantella>/interface_configs/
├── character_db/          → copy to <Pantella>/character_db/
├── metadata.json
└── README.md
```

The zip is automatically attached to the GitHub Release **and** uploaded to Nexus Mods.

---

## One-Time Setup (before first release)

### 1. Create the Nexus Mods mod page
- Go to https://www.nexusmods.com → create a new mod page
- Game: **World of Warcraft**, Category: **Utilities**
- Note your **Mod ID** (number in the URL, e.g. `nexusmods.com/worldofwarcraft/mods/1234`)

### 2. Get your Nexus Mods API key
- https://www.nexusmods.com/users/myaccount?tab=api
- Generate a Personal API Key

### 3. Add GitHub Secrets & Variables
Repo → Settings → Secrets and variables → Actions:

| Type | Name | Value |
|------|------|-------|
| Secret | `NEXUSMODS_API_KEY` | Your Nexus API key |
| Variable | `NEXUSMODS_FILE_ID` | Leave **empty** for the first upload. After the first release, Nexus assigns a file ID — set it here so future releases update the same file entry. |

---

## Releasing

```bash
# 1. Make sure master is clean and all PRs merged
git checkout master && git pull

# 2. Tag the release (follow Mantella's format)
git tag v0.1.0
git push --tags

# 3. Go to GitHub → Releases → Draft a new release
#    - Pick the tag you just pushed
#    - Write changelog (copy from PR descriptions)
#    - Click "Publish release"
#    → workflow fires automatically, zip built + uploaded to Nexus
```

## Version Format
Mirror Mantella upstream: `v0.x.x` for early releases, `v1.x.x` for stable.
