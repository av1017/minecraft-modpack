# Our World modpack

The mod list for our Fabric 26.3 Minecraft world. Every PC that plays together over LAN syncs from this repo, so everyone has the same mods.

The repo stores a **list** of mods (`mods.json`), not the mod files. The sync script downloads each mod from Modrinth, as the mod authors require, and checks it against a SHA-1 checksum before installing it.

## Mods
| Mod | What it does | Needed for LAN? |
|---|---|---|
| Wool Tweaks | Wool → 4 string; re-dye wool, beds, carpets | Yes |
| Farmer's Delight Refabricated | Cooking, new crops, rich soil, rope | Yes |
| Rustic Delight | Farmable cotton → string, coffee, peppers, pancakes | Yes |
| Fabric API, Cloth Config, Collective, Fabric Language Kotlin, Text Placeholder API | Libraries the other mods need | Yes |
| Inventory Profiles Next (+ libIPN) | Sort buttons, slot locking, tool auto-replace | No (client-only) |
| Mouse Tweaks | Faster item dragging and scrolling | No (client-only) |
| Mod Menu | In-game Mods button and settings | No (client-only) |

Exact versions are in [`mods.json`](mods.json).

## Set up a new PC
1. **Install Minecraft Java Edition** and sign in.
2. **Play vanilla 26.3 once** (Latest Release), reach the title screen, then quit.
3. **Close the game and launcher.**
4. **Clone this repo:** `git clone https://github.com/av1017/minecraft-modpack.git`
5. **Run the sync:** double-click `Sync mods.bat`. Or open Claude Code in the folder and say *"Read CLAUDE.md and sync my Minecraft mods."*
6. **Play:** in the launcher, choose **Fabric 26.3 (Modded)** and press Play.

## After someone changes the mods
Close Minecraft, then in the repo folder:
```
git pull
```
and double-click `Sync mods.bat`. The sync makes your mods folder match `mods.json` exactly. Anything it removes goes to `.minecraft\setup-backups\`.

## Changing the mods
```
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\add-mod.ps1 -Slug <modrinth-slug> -DryRun
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\add-mod.ps1 -Slug <modrinth-slug>
```
The slug is the name in the Modrinth URL: `modrinth.com/mod/<slug>`. The tool:
- picks the newest release built for Fabric 26.3
- adds any required libraries
- updates a mod that's already listed

Then run the sync, **test in-game**, and commit and push. To remove a mod, delete its entry from `mods.json`, but first check that nothing else needs it.

## Playing together
1. The host opens the world on the Fabric profile, presses Esc, clicks **Open to LAN**, then **Start LAN World**.
2. Everyone else opens the Fabric profile, goes to **Multiplayer**, and finds the world under **LAN World(s)**.

Everyone must be on the same network with the same mods. If Windows Firewall asks about Java, allow it on private networks.
