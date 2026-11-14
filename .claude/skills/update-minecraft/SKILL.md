---
name: update-minecraft
description: Update this PC's Minecraft packs for Avery's server (Cobblemon and Alaskan Wilderness) to the latest version, and explain any problem in plain words. Use when the user types /update-minecraft or asks to update, sync or fix their Minecraft mods for Avery's server.
---

# Update Minecraft (Avery's server)

You're helping a friend of Avery's update their game. They're not a programmer: keep messages short and plain, and say what to click.

## Steps
1. **Minecraft must be closed.** Check for running `javaw.exe`/`java.exe` (Minecraft) and the Minecraft Launcher. If either is open, ask the user to close both and wait for them to say so. Never close them yourself.
2. **Get the latest pack.** In this repo folder run `git pull --ff-only`.
   - If it fails because of local changes, show `git status` and stop: don't reset, stash or delete anything without the user saying so, and suggest they send the output to Avery.
3. **Dry-run both packs** and summarize what would change, in one or two lines each:
   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File .\sync.ps1 -Pack cobblemon -DryRun
   powershell -NoProfile -ExecutionPolicy Bypass -File .\sync.ps1 -Pack alaska-fabric -DryRun
   ```
4. **Sync both** (same commands without `-DryRun`).
5. **Report**: what was installed, removed or fixed, in plain words. If the sync said a config fix "waits for the mod's first launch", tell them to launch the profile once, close it, and run `/update-minecraft` (or `Update Minecraft.bat`) again.

## Rules
- Don't edit `mods.json`, `keys.txt` or anything else in this repo, and never commit or push. This copy only receives updates from Avery.
- If a step fails, stop, show the error, and explain it plainly. Common ones:
  - **"Minecraft or its launcher is still open"**: close both, then retry.
  - **A download or SHA-1 mismatch**: retry once; if it repeats, Avery needs to look at it.
  - **Git isn't installed**: the user can still double-click `Update Minecraft.bat` (it syncs the pack as it is) and ask Avery for help with Git.
- Ask before anything not on this list.

## Server reminders (when the user asks)
- Address: `192.168.1.4` at Avery's place; elsewhere, with Tailscale on: `homeserver.tail5e6af0.ts.net`.
- Cobble Valley is the default world. Type `!alaska` in chat (open chat with T, not /) to switch; `!cobblemon` switches back.
