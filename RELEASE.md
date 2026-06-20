# Release Process

## Automated Pipeline

Every tagged release automatically:
1. Builds a clean `pantella-wow-vX.Y.Z.zip` (no dev files, no tests)
2. Attaches it to the GitHub Release
3. Uploads it to the Nexus Mods mod page

## One-Time Setup (do before first release)

### 1. Create the Nexus Mods mod page
- Go to https://www.nexusmods.com and create a new mod page
- Category: **Utilities** under World of Warcraft (or the nearest equivalent)
- Note down your **Mod ID** (the number in the URL)

### 2. Get your Nexus Mods API key
- Go to https://www.nexusmods.com/users/myaccount?tab=api
- Generate a Personal API Key

### 3. Add GitHub Secrets & Variables
In your repo → Settings → Secrets and variables → Actions:

| Type | Name | Value |
|------|------|-------|
| Secret | `NEXUSMODS_API_KEY` | Your Nexus API key |
| Variable | `NEXUSMODS_FILE_ID` | Leave blank for first upload; Nexus assigns a file ID on first upload. Set this after the first release. |

### 4. Register with Vortex
To make the mod installable via Vortex one-click:
- Open a PR at https://github.com/Nexus-Mods/Vortex-Backend
- Add your mod ID to the WoW game manifest
- Nexus staff review and merge — this is a one-time manual step

## Releasing

```bash
# Merge all PRs to master first, then:
git tag v1.0.0
git push --tags
# Then create a GitHub Release from that tag
# The workflow fires automatically on release publish
```

## Version Format
Follow Pantella upstream: `b0.x.x` for beta, `v1.x.x` for stable.
