# Our Minecraft modpacks

**Guide website:** https://av1017.github.io/minecraft-modpack/ (mods, controls, Cobblemon, survival strategy)

Mod lists for the Minecraft worlds we play together over LAN. Every PC syncs from this repo, so everyone has the same mods.

The repo stores **lists** of mods, not the mod files. The sync script downloads each mod from Modrinth, as the mod authors require, and checks it against a SHA-1 checksum before installing it.

## The packs
| Pack | Launcher profile | Minecraft | Game folder | Sync with |
|---|---|---|---|---|
| **our-world** | Fabric 26.3 (Modded) | 26.3 | `%APPDATA%\.minecraft` | `Sync Our World.bat` |
| **cobblemon** | Cobblemon 1.21.1 | 1.21.1 | `%APPDATA%\.minecraft-cobblemon` | `Sync Cobblemon.bat` |

Each pack has its own game folder, with its own worlds, mods, and settings, so they never interfere with each other. Exact versions are in `packs/<pack>/mods.json`.

### our-world
- **Mods:** Wool Tweaks, Farmer's Delight, Rustic Delight, inventory sorting (Inventory Profiles Next, Mouse Tweaks, Mod Menu), EMF + ETF for animated mobs, and performance mods (Sodium, Lithium, FerriteCore), plus the libraries they need. The profile gets 4 GB of memory.
- **Texture pack:** Fresh Animations.

### cobblemon
- **Cobblemon:** catch, battle, evolve, and ride Pokémon. A fan-made mod with original models.
- **Xaero's Minimap + Xaero's World Map:** a corner minimap, a full-screen map, and waypoints.
- **Also included:** Farmer's Delight, Rustic Delight, Wool Tweaks, the same inventory sorting mods, EMF + ETF, performance mods (Sodium, Lithium, FerriteCore), and libraries. The profile gets 6 GB of memory.
- **Texture packs:** Cobblemon Interface (+ Modded), E19 Cobblemon Minimap Icons, Fresh Animations.

### Look: Faithful 32x and shaders
- **Both packs:** Faithful 32x, Fast Better Grass, and Ashen 16x. Ashen is installed but off, as an alternative; swap them in Options → Resource Packs.
- **Cobblemon only:** Motschen's Better Leaves (no 26.3 version).
- **Shaders:** Iris + Complementary Reimagined in both packs. The sync installs the shader pack but doesn't turn it on. Turn it on in **Options → Video Settings → Shader Packs**, and pick a lower profile there if the framerate drops.

### Texture packs
The sync installs each pack's texture packs into its `resourcepacks` folder and switches them on the first time. After that, each player controls them in **Options → Resource Packs**. The sync never turns a pack back on, and never deletes texture packs it didn't install. Texture packs don't need to match for LAN.

## Set up a new PC
1. **Install Minecraft Java Edition** and sign in. Play vanilla once, then close the game and launcher.
2. **Clone this repo:** `git clone https://github.com/av1017/minecraft-modpack.git`
3. **Run the sync** for each pack you want: double-click `Sync Our World.bat` and/or `Sync Cobblemon.bat`. Or open Claude Code in the folder and say *"Read CLAUDE.md and sync my Minecraft mods."*
4. **Play:** in the launcher, pick the pack's profile and press Play. A pack's first launch is slower, because the launcher downloads that Minecraft version.

## After someone changes the mods
Close Minecraft, then `git pull` in the repo folder and run the sync file for the pack that changed. The sync makes the pack's mods folder match its list exactly. Anything it removes goes to `.minecraft\setup-backups\`.

## Changing the mods
```
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\add-mod.ps1 -Pack <pack> -Slug <slug> -DryRun
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\add-mod.ps1 -Pack <pack> -Slug <slug>
```
The slug is the name in the Modrinth URL: `modrinth.com/mod/<slug>`. For several mods, separate slugs with commas. The tool:
- picks the newest release for the pack's Minecraft version
- adds any required libraries
- updates a mod that's already listed

For texture packs, add `-ResourcePack`. Order matters: later packs load on top, so add a pack's add-ons after the pack itself. Some packs only publish "beta" versions (Fresh Animations does); add `-AllowBeta` for those.

Then run the sync, **test in-game**, and commit and push.

## Playing together
1. The host opens the world on the pack's profile, presses Esc, clicks **Open to LAN**, then **Start LAN World**.
2. Everyone else opens the **same profile**, goes to **Multiplayer**, and finds the world under **LAN World(s)**.

Everyone needs the same pack synced, and you must be on the same network. If Windows Firewall asks about Java, allow it on private networks.

**If someone joins and spawns as a brand-new player,** have them leave right away. Their real progress is still saved. Both players should fully quit Minecraft and the launcher, reopen, and rejoin. This happens when Minecraft can't verify the joining player's Microsoft sign-in.
