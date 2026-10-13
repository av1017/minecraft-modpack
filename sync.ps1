<#
  Makes this PC match one of the packs in packs\<name>\mods.json.
  Windows PowerShell 5.1 compatible. Run from the repo folder:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\sync.ps1 -Pack our-world -DryRun
    powershell -NoProfile -ExecutionPolicy Bypass -File .\sync.ps1 -Pack cobblemon

  -Pack          Which pack to sync (a folder name under packs\). Default: our-world.
  -DryRun        Check everything and print what would change, without changing anything.
  -MinecraftDir  The launcher folder (default %APPDATA%\.minecraft). Packs with their own
                 game folder put it next to this one, e.g. %APPDATA%\.minecraft-cobblemon.
  -AllowRunning  Testing only: skip the "Minecraft must be closed" check.

  Mods are downloaded from Modrinth (as their authors require) and checked
  against the SHA-1 in mods.json before anything is changed.
#>
param(
  [string]$Pack = "our-world",
  [switch]$DryRun,
  [string]$MinecraftDir = (Join-Path $env:APPDATA ".minecraft"),
  [switch]$AllowRunning
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$repo      = Split-Path -Parent $MyInvocation.MyCommand.Path
$stamp     = Get-Date -Format "yyyyMMdd-HHmmss"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Step($msg) { Write-Host "`n== $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "   OK   $msg" -ForegroundColor Green }
function Plan($msg) { Write-Host "   PLAN $msg" -ForegroundColor Yellow }
function Note($msg) { Write-Host "   NOTE $msg" -ForegroundColor DarkYellow }
function Fail($msg) { Write-Host "`nSTOPPED: $msg" -ForegroundColor Red; exit 1 }
function Sha1Of($path) { (Get-FileHash -Algorithm SHA1 -LiteralPath $path).Hash.ToLower() }

if ($DryRun) { Write-Host "DRY RUN: nothing will be changed." -ForegroundColor Yellow }

# Manifest and loader file from the repo
$manifestPath = Join-Path $repo "packs\$Pack\mods.json"
if (-not (Test-Path $manifestPath)) {
  $available = (Get-ChildItem (Join-Path $repo "packs") -Directory | Select-Object -ExpandProperty Name) -join ", "
  Fail "No pack named '$Pack'. Available packs: $available"
}
$m = [System.IO.File]::ReadAllText($manifestPath) | ConvertFrom-Json
$mcVersion  = $m.minecraft
$versionId  = $m.loader.version_id
$profileKey = $m.profile.key
$loaderJson = Join-Path $repo ("loader\" + $versionId + ".json")
if (-not (Test-Path $loaderJson)) { Fail "Loader file loader\$versionId.json is missing from the repo." }
if ((Sha1Of $loaderJson) -ne $m.loader.sha1.ToLower()) { Fail "loader\$versionId.json doesn't match its checksum in mods.json." }

# Where this pack's mods, worlds, and settings live
$gameDir = $MinecraftDir
if ($m.game_dir) { $gameDir = Join-Path (Split-Path -Parent $MinecraftDir) $m.game_dir }
Write-Host "Pack: $Pack ($($m.profile.name), Minecraft $mcVersion)"

# 1. Minecraft is installed
Step "Checking Minecraft install at $MinecraftDir"
if (-not (Test-Path $MinecraftDir)) { Fail "No .minecraft folder found. Install Minecraft Java Edition and launch it once first." }
$profilesPath = Join-Path $MinecraftDir "launcher_profiles.json"
if (-not (Test-Path $profilesPath)) { Fail "launcher_profiles.json is missing. Open the Minecraft Launcher once, close it, and re-run." }
Ok "Found .minecraft and launcher profiles"
if (-not (Test-Path (Join-Path $MinecraftDir "versions\$mcVersion\$mcVersion.json"))) {
  Note "Minecraft $mcVersion isn't downloaded yet. The launcher downloads it automatically the first time you play this profile."
}

# 2. Minecraft is closed
Step "Checking that Minecraft is closed"
$running = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match '^(Minecraft|MinecraftLauncher|javaw)$' }
if ($running -and -not $AllowRunning) { Fail "Minecraft or its launcher is still open. Close both completely, then re-run." }
Ok "Minecraft is not running"

# 3. Work out every change before making any
Step "Comparing this PC with packs\$Pack\mods.json"
if ($gameDir -ne $MinecraftDir) { Write-Host "   Game folder: $gameDir" }
$modsDir = Join-Path $gameDir "mods"
$wanted = @{}
foreach ($mod in $m.mods) { $wanted[$mod.filename] = $mod }
$present = @()
if (Test-Path $modsDir) { $present = @(Get-ChildItem -LiteralPath $modsDir -File) }

$toRemove = @($present | Where-Object { -not $wanted.ContainsKey($_.Name) })
$toInstall = @()
foreach ($mod in $m.mods) {
  $dst = Join-Path $modsDir $mod.filename
  if (-not ((Test-Path -LiteralPath $dst) -and ((Sha1Of $dst) -eq $mod.sha1.ToLower()))) { $toInstall += $mod }
}
$unchanged = $m.mods.Count - $toInstall.Count

$versionFile = Join-Path $MinecraftDir "versions\$versionId\$versionId.json"
$needLoader = -not ((Test-Path $versionFile) -and ((Sha1Of $versionFile) -eq $m.loader.sha1.ToLower()))

$profiles = [System.IO.File]::ReadAllText($profilesPath) | ConvertFrom-Json
if (-not $profiles.profiles) { Fail "launcher_profiles.json has no 'profiles' section; open the launcher once and re-run." }
$currentProfile = $null
if ($profiles.profiles.PSObject.Properties.Name -contains $profileKey) { $currentProfile = $profiles.profiles.$profileKey }
$wantGameDir = $null
if ($gameDir -ne $MinecraftDir) { $wantGameDir = $gameDir }

# Memory for the profile. Never more than a third of this PC's RAM, never less than 2 GB.
$wantJavaArgs = $null
if ($m.profile.memory_gb) {
  $totalGb = [math]::Floor((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
  $memGb = [math]::Max(2, [math]::Min([int]$m.profile.memory_gb, [math]::Floor($totalGb / 3)))
  $wantJavaArgs = "-Xmx${memGb}G -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200"
  if ($memGb -lt [int]$m.profile.memory_gb) { Note "This PC has $totalGb GB of RAM, so Minecraft gets $memGb GB instead of the pack's $($m.profile.memory_gb) GB." }
}
$needProfile = -not ($currentProfile -and $currentProfile.lastVersionId -eq $versionId -and $currentProfile.gameDir -eq $wantGameDir -and $currentProfile.javaArgs -eq $wantJavaArgs)

# Resource packs: install listed ones that are missing or changed. Never delete other packs
# (players may have their own). Newly installed packs are switched on, in list order.
$rpDir = Join-Path $gameDir "resourcepacks"
$rpList = @()
if ($m.PSObject.Properties.Name -contains "resourcepacks") { $rpList = @($m.resourcepacks | Where-Object { $_ }) }
$rpToInstall = @()
foreach ($rp in $rpList) {
  $dst = Join-Path $rpDir $rp.filename
  if (-not ((Test-Path -LiteralPath $dst) -and ((Sha1Of $dst) -eq $rp.sha1.ToLower()))) { $rpToInstall += $rp }
}

# Shader packs: installed into <game folder>\shaderpacks, never switched on (graphics cards differ;
# each player turns shaders on in Options > Video Settings > Shader Packs).
$spDir = Join-Path $gameDir "shaderpacks"
$spList = @()
if ($m.PSObject.Properties.Name -contains "shaderpacks") { $spList = @($m.shaderpacks | Where-Object { $_ }) }
$spToInstall = @()
foreach ($sp in $spList) {
  $dst = Join-Path $spDir $sp.filename
  if (-not ((Test-Path -LiteralPath $dst) -and ((Sha1Of $dst) -eq $sp.sha1.ToLower()))) { $spToInstall += $sp }
}

# A new separate game folder starts with default settings; copy your existing settings and keybinds once.
$srcOptions = Join-Path $MinecraftDir "options.txt"
$dstOptions = Join-Path $gameDir "options.txt"
$needOptions = ($gameDir -ne $MinecraftDir) -and (Test-Path $srcOptions) -and -not (Test-Path $dstOptions)

# Keybind fixes for clashes between mods. Each entry moves "key" from its clashing default ("from") to "to".
# It only acts if the key isn't in options.txt yet (game hasn't saved it) or still equals "from",
# so a key a player changed on purpose is never touched.
$keyFixes = @()
if ($m.PSObject.Properties.Name -contains "keybinds") { $keyFixes = @($m.keybinds | Where-Object { $_ }) }
$keyChanges = @()
$keyOptionsFile = $dstOptions
if (-not (Test-Path $keyOptionsFile) -and $needOptions) { $keyOptionsFile = $srcOptions }   # will be copied in first
if ($keyFixes.Count -gt 0 -and (Test-Path $keyOptionsFile)) {
  $current = @{}
  foreach ($l in [System.IO.File]::ReadAllLines($keyOptionsFile)) { if ($l -match '^(key_[^:]+):(.*)$') { $current[$Matches[1]] = $Matches[2] } }
  foreach ($k in $keyFixes) {
    $has = $current.ContainsKey($k.key)
    if ((-not $has) -or $current[$k.key] -eq $k.from) {
      if (-not ($has -and $current[$k.key] -eq $k.to)) { $keyChanges += $k }
    }
  }
}

foreach ($f in $toRemove)    { Plan "Remove (not in mods.json): $($f.Name)" }
foreach ($k in $keyChanges)  { Plan "Keybind fix: $($k.key) -> $($k.to) ($($k.why))" }
foreach ($mod in $toInstall) { Plan "Install: $($mod.name) $($mod.version)" }
foreach ($rp in $rpToInstall) { Plan "Install resource pack: $($rp.name) $($rp.version)" }
foreach ($sp in $spToInstall) { Plan "Install shader pack: $($sp.name) $($sp.version)" }
if ($needLoader)  { Plan "Install Fabric loader version $versionId" }
if ($needProfile) {
  $memNote = ""; if ($wantJavaArgs) { $memNote = " with " + ([regex]::Match($wantJavaArgs, '-Xmx(\d+)G').Groups[1].Value) + " GB of memory" }
  Plan "Set launcher profile '$($m.profile.name)' to $versionId$memNote"
}
if ($needOptions) { Plan "Copy your game settings and keybinds into the new game folder" }
Ok "$unchanged of $($m.mods.Count) mods already up to date"
if ($rpList.Count -gt 0) { Ok "$($rpList.Count - $rpToInstall.Count) of $($rpList.Count) resource packs already up to date" }

if ($spList.Count -gt 0) { Ok "$($spList.Count - $spToInstall.Count) of $($spList.Count) shader packs already up to date" }

$changes = $toRemove.Count + $toInstall.Count + $rpToInstall.Count + $spToInstall.Count + $keyChanges.Count + [int]$needLoader + [int]$needProfile + [int]$needOptions
if ($changes -eq 0) {
  Write-Host "`nALREADY IN SYNC. Nothing to change." -ForegroundColor Green
  exit 0
}

# 4. Download and verify new mods into a staging folder first
$staging = Join-Path $env:TEMP "minecraft-modpack-$stamp"
$downloads = @($toInstall) + @($rpToInstall) + @($spToInstall)
if ($downloads.Count -gt 0) {
  Step "Downloading $($downloads.Count) file(s) from Modrinth"
  New-Item -ItemType Directory -Force -Path $staging | Out-Null
  $n = 0
  foreach ($mod in $downloads) {
    $tmp = Join-Path $staging $mod.filename
    # Download to a plain name first: -OutFile treats [ ] in file names as wildcards.
    $plain = Join-Path $staging ("download-" + ($n++) + ".part")
    try { Invoke-WebRequest -UseBasicParsing -Uri $mod.url -OutFile $plain -Headers @{ "User-Agent" = "av1017/minecraft-modpack" } }
    catch { Fail "Couldn't download $($mod.name): $($_.Exception.Message). Nothing was changed." }
    Move-Item -LiteralPath $plain -Destination $tmp -Force
    if ((Sha1Of $tmp) -ne $mod.sha1.ToLower()) { Fail "Downloaded $($mod.filename) doesn't match its checksum. Nothing was changed." }
    Ok "Downloaded and verified $($mod.filename)"
  }
}

if ($DryRun) {
  if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
  Write-Host "`nDRY RUN COMPLETE. $changes change(s) planned and all downloads verified; run again without -DryRun to apply." -ForegroundColor Green
  exit 0
}

# 5. Back up, then apply
Step "Applying changes"
$backupDir = Join-Path $MinecraftDir "setup-backups\$Pack-$stamp"
New-Item -ItemType Directory -Force -Path $backupDir, $modsDir | Out-Null
Copy-Item -LiteralPath $profilesPath -Destination (Join-Path $backupDir "launcher_profiles.json")
Ok "Backed up launcher_profiles.json"

if ($toRemove.Count -gt 0) {
  $modsBackup = Join-Path $backupDir "mods"
  New-Item -ItemType Directory -Force -Path $modsBackup | Out-Null
  foreach ($f in $toRemove) { Move-Item -LiteralPath $f.FullName -Destination $modsBackup -Force }
  Ok "Moved $($toRemove.Count) removed mod(s) to the backup"
}
foreach ($mod in $toInstall) {
  $dst = Join-Path $modsDir $mod.filename
  Copy-Item -LiteralPath (Join-Path $staging $mod.filename) -Destination $dst -Force
  if ((Sha1Of $dst) -ne $mod.sha1.ToLower()) { Fail "Installed $($mod.filename) doesn't match its checksum." }
}
if ($toInstall.Count -gt 0) { Ok "Installed $($toInstall.Count) mod(s)" }

$rpNew = @()
if ($rpToInstall.Count -gt 0) {
  New-Item -ItemType Directory -Force -Path $rpDir | Out-Null
  foreach ($rp in $rpToInstall) {
    $dst = Join-Path $rpDir $rp.filename
    if (-not (Test-Path -LiteralPath $dst)) { $rpNew += $rp }
    Copy-Item -LiteralPath (Join-Path $staging $rp.filename) -Destination $dst -Force
    if ((Sha1Of $dst) -ne $rp.sha1.ToLower()) { Fail "Installed $($rp.filename) doesn't match its checksum." }
  }
  Ok "Installed $($rpToInstall.Count) resource pack(s)"
}
if ($spToInstall.Count -gt 0) {
  New-Item -ItemType Directory -Force -Path $spDir | Out-Null
  foreach ($sp in $spToInstall) {
    $dst = Join-Path $spDir $sp.filename
    Copy-Item -LiteralPath (Join-Path $staging $sp.filename) -Destination $dst -Force
    if ((Sha1Of $dst) -ne $sp.sha1.ToLower()) { Fail "Installed $($sp.filename) doesn't match its checksum." }
  }
  Ok "Installed $($spToInstall.Count) shader pack(s) (turn on in Options > Video Settings > Shader Packs)"
}
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }

if ($needLoader) {
  New-Item -ItemType Directory -Force -Path (Split-Path $versionFile) | Out-Null
  Copy-Item -LiteralPath $loaderJson -Destination $versionFile -Force
  Ok "Installed Fabric loader version $versionId"
}

if ($needOptions) {
  Copy-Item -LiteralPath $srcOptions -Destination $dstOptions
  Ok "Copied game settings and keybinds"
}

# Apply keybind fixes (worked out above).
if ($keyChanges.Count -gt 0) {
  if (-not (Test-Path $dstOptions)) {
    Note "No options.txt yet; keybind fixes will apply on the next sync after your first launch."
  } else {
    $optBackup = Join-Path $backupDir "options.txt"
    if (-not (Test-Path $optBackup)) { Copy-Item -LiteralPath $dstOptions -Destination $optBackup }
    $raw = [System.IO.File]::ReadAllText($dstOptions)
    $nl = "`n"; if ($raw.Contains("`r`n")) { $nl = "`r`n" }
    $lines = [System.Collections.ArrayList]@($raw.TrimEnd("`r", "`n") -split [regex]::Escape($nl))
    foreach ($k in $keyChanges) {
      $idx = -1
      for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -like ($k.key + ":*")) { $idx = $i } }
      if ($idx -ge 0) { $lines[$idx] = $k.key + ":" + $k.to } else { [void]$lines.Add($k.key + ":" + $k.to) }
    }
    [System.IO.File]::WriteAllText($dstOptions, (($lines -join $nl) + $nl), $utf8NoBom)
    Ok "Applied $($keyChanges.Count) keybind fix(es)"
  }
}

# Switch on resource packs installed for the first time (later entries load on top).
if ($rpNew.Count -gt 0) {
  if (-not (Test-Path $dstOptions)) {
    Note "No options.txt yet; turn the new resource packs on in Options > Resource Packs after your first launch."
  } else {
    $optBackup = Join-Path $backupDir "options.txt"
    if (-not (Test-Path $optBackup)) { Copy-Item -LiteralPath $dstOptions -Destination $optBackup }   # keep the original
    $lines = [System.Collections.ArrayList]@([System.IO.File]::ReadAllLines($dstOptions))
    $idx = -1
    for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -like "resourcePacks:*") { $idx = $i } }
    $enabled = New-Object System.Collections.ArrayList
    if ($idx -ge 0) {
      # Windows PowerShell 5.1 emits a JSON array as ONE object; assign first, then iterate to unroll it.
      $parsed = ConvertFrom-Json $lines[$idx].Substring("resourcePacks:".Length)
      foreach ($e in $parsed) { [void]$enabled.Add([string]$e) }
    } else { [void]$enabled.Add("vanilla"); [void]$enabled.Add("fabric") }
    # Put each new pack in its list position: just below the next listed pack that's already on, else on top.
    $switchedOn = 0
    for ($i = 0; $i -lt $rpList.Count; $i++) {
      $rp = $rpList[$i]
      if (-not ($rpNew -contains $rp)) { continue }
      if ($rp.PSObject.Properties.Name -contains "enabled" -and $rp.enabled -eq $false) { continue }   # installed, but left off
      $entry = "file/" + $rp.filename
      if ($enabled -contains $entry) { continue }
      $insertAt = -1
      for ($j = $i + 1; $j -lt $rpList.Count -and $insertAt -lt 0; $j++) {
        $later = $enabled.IndexOf("file/" + $rpList[$j].filename)
        if ($later -ge 0) { $insertAt = $later }
      }
      if ($insertAt -ge 0) { $enabled.Insert($insertAt, $entry) } else { [void]$enabled.Add($entry) }
      $switchedOn++
    }
    $quoted = @($enabled | ForEach-Object { '"' + ($_ -replace '\\', '\\' -replace '"', '\"') + '"' })
    $newLine = "resourcePacks:[" + ($quoted -join ",") + "]"
    if ($idx -ge 0) { $lines[$idx] = $newLine } else { [void]$lines.Add($newLine) }
    $nl = "`n"; if ([System.IO.File]::ReadAllText($dstOptions).Contains("`r`n")) { $nl = "`r`n" }   # keep Minecraft's line endings
    [System.IO.File]::WriteAllText($dstOptions, (($lines -join $nl) + $nl), $utf8NoBom)
    $leftOff = $rpNew.Count - $switchedOn
    $offNote = ""; if ($leftOff -gt 0) { $offNote = "; $leftOff installed but left off" }
    Ok "Switched on $switchedOn new resource pack(s)$offNote (change order or turn off in Options > Resource Packs)"
  }
}

if ($needProfile) {
  $now = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.000Z")
  $newProfile = [pscustomobject]@{
    created = $now; icon = $m.profile.icon; lastUsed = $now
    lastVersionId = $versionId; name = $m.profile.name; type = "custom"
  }
  if ($wantGameDir) { $newProfile | Add-Member -NotePropertyName gameDir -NotePropertyValue $wantGameDir }
  if ($wantJavaArgs) { $newProfile | Add-Member -NotePropertyName javaArgs -NotePropertyValue $wantJavaArgs }
  if ($currentProfile) { $profiles.profiles.$profileKey = $newProfile }
  else { $profiles.profiles | Add-Member -NotePropertyName $profileKey -NotePropertyValue $newProfile }
  [System.IO.File]::WriteAllText($profilesPath, ($profiles | ConvertTo-Json -Depth 20), $utf8NoBom)
  $null = [System.IO.File]::ReadAllText($profilesPath) | ConvertFrom-Json
  Ok "Launcher profile saved and launcher_profiles.json still parses"
}

Write-Host "`nSYNC COMPLETE. Choose '$($m.profile.name)' in the launcher and press Play." -ForegroundColor Green
Write-Host "Backup of the previous state: $backupDir"
