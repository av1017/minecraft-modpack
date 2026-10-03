# CLAUDE.md: Our World modpack

This repo defines the exact Minecraft mods for a Fabric 26.3 world that two people play together over LAN. Each PC syncs from it. You'll be asked to do one of two things: **sync** a PC to the repo, or **change** the mods.

## How it works
- **`mods.json`** is the source of truth:
  - the Minecraft version and Fabric loader version
  - the launcher profile settings
  - each mod's Modrinth project and version ID, file name, download URL, SHA-1, and `side` (`both` or `client`)
- **`loader/fabric-loader-0.19.5-26.3.json`** is the launcher version file for Fabric, checksummed in `mods.json`.
- **`sync.ps1`** makes `%APPDATA%\.minecraft` match `mods.json`:
  - downloads mods from Modrinth into a temp folder and verifies their SHA-1 before touching anything
  - removes jars not in the list, moving them to `.minecraft\setup-backups\<timestamp>\`
  - installs the loader and launcher profile if they're missing
  - backs up `launcher_profiles.json` first

  It supports `-DryRun` and `-MinecraftDir`, and running it twice is safe.
- **`tools/add-mod.ps1`** adds or updates mods in `mods.json` from Modrinth. It only picks releases built for this pack's loader and Minecraft version, and adds required dependencies. Dependencies already in the pack keep their current version.

## Rules
- **Mod files never go in the repo.** Some mod licenses forbid re-hosting (Wool Tweaks requires downloads to stay on CurseForge or Modrinth). `.gitignore` blocks `*.jar`.
- **Every PC must match.** LAN fails if gameplay mods (`side: both`) differ. Client-only mods can differ, but keep them in sync anyway.
- **Don't edit `mods.json` by hand except to remove an entry.** Use `tools/add-mod.ps1`, so URLs and checksums come straight from Modrinth.
- **Never touch `saves/`.** Worlds aren't part of this repo.
- **Don't install Java.** The Minecraft launcher bundles it.
- **Don't force-close Minecraft.** Ask the user to close it.
- Use `-AllowRunning` only for tests against a non-real `-MinecraftDir`.

## Task: sync this PC
1. **Confirm:**
   - Minecraft Java is installed.
   - Vanilla 26.3 has been launched once (`.minecraft\versions\26.3` exists).
   - The game and launcher are closed.
2. **Pull** if this is an existing clone: `git pull`.
3. **Dry run** and read the planned changes:
   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File .\sync.ps1 -DryRun
   ```
   If it prints `STOPPED: ...`, fix that one thing (the message says what) and re-run. Don't work around checks.
4. **Sync:**
   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File .\sync.ps1
   ```
5. **Tell the user** what changed and where the backup is. To play: launcher → **Fabric 26.3 (Modded)** → Play. The first launch is slower.

If `.minecraft` isn't at `%APPDATA%\.minecraft`, find the folder containing `launcher_profiles.json` and `versions\26.3`, and pass `-MinecraftDir "<path>"`.

## Task: add, update, or remove a mod
1. **Find the slug** in the mod's Modrinth URL. Confirm the mod has a **Fabric 26.3** release. Before adding it, tell the user if it's client-only or if it changes the world (new blocks or items).
2. **Preview, then apply:**
   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\add-mod.ps1 -Slug <slug> -DryRun
   powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\add-mod.ps1 -Slug <slug>
   ```
   To update every listed mod, pass all their slugs. Updates of gameplay mods need the same caution as adding them.
3. **To remove a mod:** delete its entry from `mods.json`. First check that no remaining mod lists it as a required dependency (look up each mod's version on Modrinth: `/v2/version/<version_id>`). Removing a mod that added blocks or items deletes those from the world.
4. **Back up the world** (zip the folder under `saves\`) before syncing changes to gameplay mods.
5. **Run the sync,** then ask the user to **launch and load the world** to confirm it works.
6. **Only then commit and push.** Use a message listing what was added, updated, or removed:
   ```
   git add mods.json && git commit -m "Add <mod> <version>" && git push
   ```
7. **Remind the user** that every other PC must `git pull` and sync before the next LAN session.

## Troubleshooting a crash
Read `.minecraft\logs\latest.log` and the newest file in `.minecraft\crash-reports\`. Look for the mod ID named in "Incompatible mods", "requires", or the top of the stack trace. A re-run of `sync.ps1 -DryRun` confirms the installed files are intact. To roll back a change, check out the previous `mods.json` from git history and sync.
