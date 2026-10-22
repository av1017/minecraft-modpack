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
  - `profile`: launcher profile key, name, icon, and `memory_gb`. The sync writes `javaArgs` with `-Xmx` set to that amount, capped at a third of the PC's RAM and never below 2 GB, plus G1GC flags. Optional `gc_args` replaces the G1 flags (Cobblemon, on Java 21, uses `-XX:+UseZGC -XX:+ZGenerational`; on Java 23+ drop `-XX:+ZGenerational`, since generational mode is the default there).
  - `mods`: each mod's Modrinth project and version ID, file name, URL, SHA-1, and `side` (`both` or `client`). For `cobblemon`, `side: both` is also the **dedicated server's** mod list (homeserver, `/srv/homeserver/services/minecraft/update-mods.py`, minus `e4mc` and `distanthorizons`). A library a `both` mod requires must be `both` too, even if Modrinth calls it client-only, or the server won't start (Athena, for CobbleFurnies).
  - `resourcepacks`: optional; texture packs in load order (later entries load on top). `"enabled": false` means installed but not switched on (e.g. an alternative to compare).
  - `shaderpacks`: optional; Iris shader packs. Installed into `<game folder>\shaderpacks` and never switched on by the sync, because graphics cards differ.
  - `keybinds`: optional; keybind fixes for clashes between mods, as `{key, from, to, why}` using `options.txt` names (`key_<translation key>`, `key.keyboard.<x>`; `key.keyboard.unknown` = unbound). The sync applies one only if that line is missing or still equals `from`, so a key the player changed is never touched.
  - `config_fixes`: optional; edits to mods' own config files for settings not in `options.txt`, as `{file, find, replace, why}`. `find` is a regex that matches only the mod's unfixed default, so a player's own change is never touched. The file is backed up first. Mods create their configs on first launch, so on a new PC these apply on the sync after the first launch. Current fixes: REI recipe key R → Y, the AutoSwitch creeper rule, and a light Distant Horizons profile. DH's defaults (256 chunks, full-chunk generation, SSAO, LOD clouds) maxed out the host laptop's GPU.
  - `config_files`: optional; whole files shipped from the repo, as `{file, source, why}`. `source` is a path in this repo (keep them under `packs/<pack>/config/`), and `file` is the destination in the game folder. The sync copies it when it's missing or differs (by SHA-1), backing up any older copy. Use only file names we own. Current: an Inventory Profiles Next integration hint (`integrationHints/travelersbackpack.json`) that hides IPN's sort/move buttons on Traveler's Backpack's `BackpackScreen`, where they covered the backpack's own buttons. IPN loads every `*.json` in that folder except the example file.
- Any mod entry can have `"pinned": true` plus `pinned_reason`; `add-mod.ps1` won't update it. Cobblemon's Sodium is pinned to 0.6.x because Iris for 1.21.1 requires Sodium 0.6.x. Unpin only when an Iris build for 1.21.1 accepts a newer Sodium (check its `fabric.mod.json`).
- **`loader/<version_id>.json`** is the launcher version file for each Fabric/Minecraft pair, checksummed in the pack's `mods.json`.
- **`sync.ps1 -Pack <pack>`** makes the PC match the pack:
  - downloads mods from Modrinth into a temp folder and verifies SHA-1 before touching anything
  - removes jars not in the list, moving them to `.minecraft\setup-backups\<pack>-<timestamp>\`
  - installs the loader file
  - creates or updates the launcher profile, including `gameDir` for packs with their own folder
  - on first setup of a separate game folder, copies `options.txt` so settings and keybinds carry over
  - installs listed texture packs into `<game folder>\resourcepacks`. It switches a pack on in `options.txt` only the first time it installs it, keeping Minecraft's CRLF line endings and the existing entries, and backs up `options.txt` first. It never deletes texture packs it didn't install, and never re-enables a pack the player turned off.
  - applies the pack's `keybinds` fixes to `options.txt` (same CRLF handling and backup), then its `config_fixes`, then places its `config_files`
  - backs up `launcher_profiles.json` before changing anything

  It supports `-DryRun` and `-MinecraftDir`, and running it twice is safe. If the pack's Minecraft version isn't downloaded yet, it prints a note; the launcher downloads it on first launch.
- **`tools/add-mod.ps1 -Pack <pack> -Slug a,b`** adds or updates mods in a pack from Modrinth. It only picks releases built for that pack's Minecraft version and adds required dependencies. Dependencies already in the pack keep their version.
  - Add `-ResourcePack` for texture packs. They keep the order given, and required mods aren't added automatically, so check the pack's page. Fresh Animations needs the `entity-model-features` and `entitytexturefeatures` mods.
  - Add `-AllowBeta` for projects that only publish betas (Fresh Animations does).
  - Add `-ShaderPack` for shader packs (Modrinth loader `iris`).
  - `side` is `client` when Modrinth says `server_side: unsupported`, except that a required dependency of a `both` mod is promoted to `both` (printed as `SIDE`), and an entry already marked `both` stays `both`.
  - Before adding a mod that depends on Sodium (like Iris), read its `fabric.mod.json` `depends` and compare it with the pack's Sodium. A mismatch stops the game from launching.

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
- **When the mods change, update the matching guide pages in the same commit:** `mods.html` for Our World mods, `cobblemon.html` for the Cobblemon pack, and `controls.html` for keybinds, `visuals.html` for texture packs and shaders. Big mods get their own page: `portalgun.html`, `backpack.html`, `gyms.html` (Radical Cobblemon Trainers + gyms).
- **Verify facts before writing them.** Read recipes and text from the installed jars, and read keybinds from the pack's `options.txt` after a launch. Before a launch, a mod's default keys are in its bytecode: the int pushed right after the `key.<mod>.<name>` string in the class that registers its key mappings (GLFW codes: 66 = B, 90 = Z, 86 = V, 295 = F6, -1 = unbound).
- **After adding a mod, check its default keys against both profiles' `options.txt`** and add a `keybinds` fix for any clash. Prefer moving the new mod's key, and update `controls.html`.
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
8. **For `cobblemon`, also update the server and the friends' pack** (both read the pushed `mods.json`):
   - Server (homeserver, over `ssh homeserver`): `cd /srv/homeserver/services/minecraft && ./update-mods.py` (dry run), then `docker compose stop && ./update-mods.py --apply && docker compose up -d`. Commit nothing there unless the compose file changes, but add a line to its `logs/YYYYMMDD.md`.
   - Friends' pack: `python -I tools/build-friends-pack.py --upload`, then tell the user to let friends know (they re-import the file; see the guide's Playing From Anywhere page).

## Friends' pack (Modrinth App, no sync script)
Friends who can't run `sync.ps1` (Mac, or no Claude) import `Reajustiene-Cobblemon.mrpack` into the Modrinth App. It's built by `tools/build-friends-pack.py` from the cobblemon `mods.json` plus `packs/cobblemon/friends/`:
- `pack.json`: name, `exclude` (e4mc), the Minecraft data version for `options.txt`, built-in resource packs to switch on, the Multiplayer server entries (`servers.dat`), and the release tag and asset name.
- `overrides/`: config files copied into the instance as-is. Currently the host's REI config (recipe key Y), AutoSwitch's use-action rules (creeper fix), and Distant Horizons' light profile (radius 48). These replace `config_fixes`, which need a first launch. The pack's `config_files` are added automatically.
- The generated `options.txt` holds only `version`, `resourcePacks` (the enabled texture packs in manifest order), and the `keybinds` fixes. Minecraft fills in defaults for everything else.

The `.mrpack` lists download URLs and hashes only (no jars), so it respects mod licenses. `--upload` replaces the asset on the `friends-pack` GitHub release, so the download link in the guide never changes: `https://github.com/av1017/minecraft-modpack/releases/download/friends-pack/Reajustiene-Cobblemon.mrpack`. `dist/` is git-ignored.

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

## Twin Portals (our own mod)
The `twinportals-local` entry in `packs/cobblemon/mods.json` is our own mod, not a Modrinth project. Its jar is a GitHub release asset on this repo (tag `twinportals-vX.Y.Z`), and the entry is `pinned`, so `add-mod.ps1` never touches it. The source lives on the host PC (`minecraftServer/portal-gun-mod`).

To ship a new version:
1. Build it there; GameTests run as part of the build.
2. Create the GitHub release with the jar.
3. Edit the entry's `version`, `filename`, `url`, and `sha1`.
4. Push.

Never push a manifest whose release asset doesn't exist yet: every other PC's sync would fail to download it.

## REI Craftable Fix (our own client mod)
The `reicraftablefix-local` entry (side `client`) is a tiny mixin mod. REI 16 runs `CraftableFilter.tick()` every 5 ticks and compares inventory maps keyed by each stack's full component hash, so a mod component with an unstable hash made REI re-run its search 4×/s and hovered tooltips flickered in craftable-only mode. The mod cancels that tick unless item ids, counts, or the open menu changed. Source: `minecraftServer/rei-craftable-fix` on the host PC (Loom, same versions as Twin Portals; build with JDK 25). Release tag `reicraftablefix-vX.Y.Z`; ship updates the same way as Twin Portals. If REI updates, check the mixin still applies (it fails soft: `required: false`).

## Craftable Templates (our own recipe mod)
The `avtemplates-local` entry is a data-only mod with a crafting recipe for every smithing template (7 diamonds + a themed item + the copy block), plus (since 1.1.0) the 26.x saddle and slime-free lead recipes that 1.21.1 lacks. Its source is `tools/craftable-templates/build.py`, and the jar is a GitHub release asset (tag `avtemplates-vX.Y.Z`). It replaces Craftable Smithing Templates 1.2 from Modrinth, whose recipes use the 1.21.2+ format and fail to load on 1.21.1 ("Parsing error loading recipe craftabletrims:…" in the log).

To ship a change: edit `RECIPES` (and bump `VERSION`), run `python tools/craftable-templates/build.py <dir>`, create the GitHub release with the jar, update the entry's `version`, `filename`, `url`, and `sha1`, then push.
