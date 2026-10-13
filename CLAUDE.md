# CLAUDE.md: Minecraft modpacks

This repo defines the exact Minecraft mods for the worlds two people play together over LAN. Each PC syncs from it. There are multiple **packs** under `packs/`, each with its own Minecraft version, launcher profile, and (optionally) its own game folder. You'll be asked to do one of two things: **sync** a PC, or **change** a pack's mods.

## Packs
| Pack | Profile | Minecraft | Game folder |
|---|---|---|---|
| `our-world` | Fabric 26.3 (Modded) | 26.3 | `%APPDATA%\.minecraft` (the default) |
| `cobblemon` | Cobblemon 1.21.1 | 1.21.1 | `%APPDATA%\.minecraft-cobblemon` |

## How it works
- **`packs/<pack>/mods.json`** is the source of truth for that pack:
  - `minecraft`: the Minecraft version
  - `game_dir`: optional; a folder next to `.minecraft` holding this pack's mods, worlds, and settings
  - `loader`: Fabric version, ID, and SHA-1
  - `profile`: launcher profile key, name, and icon
  - `mods`: each mod's Modrinth project and version ID, file name, URL, SHA-1, and `side` (`both` or `client`)
  - `resourcepacks`: optional; texture packs in load order (later entries load on top)
- **`loader/<version_id>.json`** is the launcher version file for each Fabric/Minecraft pair, checksummed in the pack's `mods.json`.
- **`sync.ps1 -Pack <pack>`** makes the PC match the pack:
  - downloads mods from Modrinth into a temp folder and verifies SHA-1 before touching anything
  - removes jars not in the list, moving them to `.minecraft\setup-backups\<pack>-<timestamp>\`
  - installs the loader file
  - creates or updates the launcher profile, including `gameDir` for packs with their own folder
  - on first setup of a separate game folder, copies `options.txt` so settings and keybinds carry over
  - installs listed texture packs into `<game folder>\resourcepacks`. It switches a pack on in `options.txt` only the first time it installs it, keeping Minecraft's CRLF line endings and the existing entries, and backs up `options.txt` first. It never deletes texture packs it didn't install, and never re-enables a pack the player turned off.
  - backs up `launcher_profiles.json` before changing anything

  It supports `-DryRun` and `-MinecraftDir`, and running it twice is safe. If the pack's Minecraft version isn't downloaded yet, it prints a note; the launcher downloads it on first launch.
- **`tools/add-mod.ps1 -Pack <pack> -Slug a,b`** adds or updates mods in a pack from Modrinth. It only picks releases built for that pack's Minecraft version and adds required dependencies. Dependencies already in the pack keep their version.
  - Add `-ResourcePack` for texture packs. They keep the order given, and required mods aren't added automatically, so check the pack's page. Fresh Animations needs the `entity-model-features` and `entitytexturefeatures` mods.
  - Add `-AllowBeta` for projects that only publish betas (Fresh Animations does).

## Guide website
`docs/` is a static HTML site published by GitHub Pages at https://av1017.github.io/minecraft-modpack/ (branch `main`, folder `/docs`). Pages are self-contained: inline CSS/JS, Google Fonts, no build step. Checklist progress is stored in each visitor's browser (`localStorage`).
- **Layout:** `index.html` is the frame: a left sidebar plus a main area (an iframe) that shows one page. The address hash picks the page (`#cobblemon`), so links and the back button work. On phones the sidebar becomes a drawer.
- **To add a page:**
  1. Create `docs/<name>.html` as a full standalone page.
  2. Add an entry to the `GROUPS` list in `index.html`.
  3. Link it from `overview.html` (the Home page) if it belongs there.
- **What the frame handles:**
  - It hides each page's `.crumb` back link when shown inside it.
  - It keeps relative links between pages inside the layout.
  - It counts each page's `<li data-id>` checklist items for the sidebar progress. Pages save under the localStorage key `mc-guide-<page>-progress-fallback`.
- **Numbered steps** (`ol.flow` / `ol.steps`) use block layout with an absolutely positioned number. Don't use `display: flex` on those `li`s: inline bold text and key badges would split into columns.
- **When the mods change, update the matching guide pages in the same commit:** `mods.html` for Our World mods, `cobblemon.html` for the Cobblemon pack, and `controls.html` for keybinds and texture packs.
- **Verify facts before writing them.** Read recipes and text from the installed jars, and read keybinds from the pack's `options.txt` after a launch.
- **Keep every page working on a phone:** keep the viewport meta, don't use fixed widths, and wrap wide tables in an `overflow-x: auto` container.
- Pushing to `main` republishes the site within a minute or two.

## Rules
- **Mod files never go in the repo.** Some licenses forbid re-hosting (Wool Tweaks requires downloads to stay on CurseForge or Modrinth). `.gitignore` blocks `*.jar`.
- **Every PC must match per pack.** LAN fails if gameplay mods differ. Client-only mods can differ, but keep them in sync anyway.
- **Never move a world between packs.** Minecraft can't load a world in an older version than the one it was played on (Our World is 26.3, Cobblemon is 1.21.1), and removing a mod deletes its blocks and items from the world.
- **Don't edit `mods.json` by hand except to remove an entry.** Use `tools/add-mod.ps1`.
- **Never touch `saves/`.** Worlds aren't part of this repo.
- **Don't install Java.** The launcher bundles it, and downloads the right Java version for each Minecraft version.
- **Don't force-close Minecraft.** Ask the user to close it.
- Use `-AllowRunning` only for tests against a non-real `-MinecraftDir`.

## Task: sync this PC
1. **Confirm:**
   - Minecraft Java is installed and has been launched once (`launcher_profiles.json` exists).
   - The game and launcher are closed.
   - Which pack(s) the user wants. If they don't say, sync both.
2. **Pull** if this is an existing clone: `git pull`.
3. **For each pack, dry run first** and read the planned changes:
   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File .\sync.ps1 -Pack <pack> -DryRun
   ```
   If it prints `STOPPED: ...`, fix that one thing and re-run. Don't work around checks.
4. **Sync:**
   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File .\sync.ps1 -Pack <pack>
   ```
5. **Tell the user** what changed and where the backup is. To play: launcher → the pack's profile → Play. A pack's first launch is slower while the launcher downloads that Minecraft version.

If `.minecraft` isn't at `%APPDATA%\.minecraft`, find the folder containing `launcher_profiles.json` and pass `-MinecraftDir "<path>"`.

## Task: add, update, or remove a mod
1. **Find the slug** in the mod's Modrinth URL. Confirm the mod has a Fabric release for the pack's Minecraft version (check `packs/<pack>/mods.json`). Before adding it, tell the user if it's client-only or if it changes the world (new blocks, items, or creatures).
2. **Preview, then apply:**
   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\add-mod.ps1 -Pack <pack> -Slug <slug> -DryRun
   powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\add-mod.ps1 -Pack <pack> -Slug <slug>
   ```
3. **To remove a mod:** delete its entry from the pack's `mods.json`. First check that no remaining mod lists it as a required dependency (look up each mod's version on Modrinth: `/v2/version/<version_id>`).
4. **Back up the pack's world** (zip its folder under the pack's game folder `saves\`) before syncing changes to gameplay mods.
5. **Run the sync,** then ask the user to **launch and load the world** to confirm it works.
6. **Only then commit and push:** `git add packs && git commit -m "<pack>: add <mod> <version>" && git push`
7. **Remind the user** that every other PC must `git pull` and sync that pack before the next LAN session.

## Task: add a new pack
1. Create `packs/<name>/mods.json` with:
   - `minecraft`
   - `game_dir` (always use a separate folder for a new pack)
   - `loader`, with the Fabric profile JSON saved to `loader/` and its SHA-1 recorded
   - `profile` (unique key and name)
   - `"mods": []`
2. Fill it with `tools/add-mod.ps1`.
3. Add a `Sync <Name>.bat` like the existing ones, and update the README and this file.

## Troubleshooting
- **Crash:** read `logs\latest.log` and the newest `crash-reports\` file in the pack's **game folder**. Look for the mod ID in "Incompatible mods", "requires", or the top of the stack trace. Re-run `sync.ps1 -Pack <pack> -DryRun` to confirm files are intact. Roll back with git history and sync.
- **A LAN player spawns as a new character:** their join line in the host's log shows "Failed to verify username but will let them in anyway!" Their real data is still in the world's `players/data/<real-uuid>.dat`, untouched. Both players should fully quit Minecraft and the launcher, reopen, and rejoin.
