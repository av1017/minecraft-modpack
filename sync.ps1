<#
  Makes this PC's Minecraft mods match mods.json exactly.
  Windows PowerShell 5.1 compatible. Run from the repo folder:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\sync.ps1 -DryRun
    powershell -NoProfile -ExecutionPolicy Bypass -File .\sync.ps1

  -DryRun        Check everything and print what would change, without changing anything.
  -MinecraftDir  Use a .minecraft folder other than %APPDATA%\.minecraft.
  -AllowRunning  Testing only: skip the "Minecraft must be closed" check.

  Mods are downloaded from Modrinth (as their authors require) and checked
  against the SHA-1 in mods.json before anything in .minecraft is changed.
#>
param(
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
function Fail($msg) { Write-Host "`nSTOPPED: $msg" -ForegroundColor Red; exit 1 }
function Sha1Of($path) { (Get-FileHash -Algorithm SHA1 -LiteralPath $path).Hash.ToLower() }

if ($DryRun) { Write-Host "DRY RUN: nothing will be changed." -ForegroundColor Yellow }

# Manifest and loader file from the repo
$manifestPath = Join-Path $repo "mods.json"
if (-not (Test-Path $manifestPath)) { Fail "mods.json not found next to sync.ps1." }
$m = [System.IO.File]::ReadAllText($manifestPath) | ConvertFrom-Json
$mcVersion  = $m.minecraft
$versionId  = $m.loader.version_id
$profileKey = $m.profile.key
$loaderJson = Join-Path $repo ("loader\" + $versionId + ".json")
if (-not (Test-Path $loaderJson)) { Fail "Loader file loader\$versionId.json is missing from the repo." }
if ((Sha1Of $loaderJson) -ne $m.loader.sha1.ToLower()) { Fail "loader\$versionId.json doesn't match its checksum in mods.json." }

# 1. Minecraft is installed and the base version has been launched once
Step "Checking Minecraft install at $MinecraftDir"
if (-not (Test-Path $MinecraftDir)) { Fail "No .minecraft folder found. Install Minecraft Java Edition and launch it once first." }
$profilesPath = Join-Path $MinecraftDir "launcher_profiles.json"
if (-not (Test-Path $profilesPath)) { Fail "launcher_profiles.json is missing. Open the Minecraft Launcher once, close it, and re-run." }
if (-not (Test-Path (Join-Path $MinecraftDir "versions\$mcVersion\$mcVersion.json"))) {
  Fail "Minecraft $mcVersion hasn't been downloaded yet. In the launcher, play vanilla $mcVersion once, quit, and re-run."
}
Ok "Found .minecraft, launcher profiles, and vanilla $mcVersion"

# 2. Minecraft is closed
Step "Checking that Minecraft is closed"
$running = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match '^(Minecraft|MinecraftLauncher|javaw)$' }
if ($running -and -not $AllowRunning) { Fail "Minecraft or its launcher is still open. Close both completely, then re-run." }
Ok "Minecraft is not running"

# 3. Work out every change before making any
Step "Comparing this PC with mods.json"
$modsDir = Join-Path $MinecraftDir "mods"
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
$needProfile = -not ($currentProfile -and $currentProfile.lastVersionId -eq $versionId)

foreach ($f in $toRemove)    { Plan "Remove (not in mods.json): $($f.Name)" }
foreach ($mod in $toInstall) { Plan "Install: $($mod.name) $($mod.version)" }
if ($needLoader)  { Plan "Install Fabric loader version $versionId" }
if ($needProfile) { Plan "Set launcher profile '$($m.profile.name)' to $versionId" }
Ok "$unchanged of $($m.mods.Count) mods already up to date"

$changes = $toRemove.Count + $toInstall.Count + [int]$needLoader + [int]$needProfile
if ($changes -eq 0) {
  Write-Host "`nALREADY IN SYNC. Nothing to change." -ForegroundColor Green
  exit 0
}

# 4. Download and verify new mods into a staging folder first
$staging = Join-Path $env:TEMP "minecraft-modpack-$stamp"
if ($toInstall.Count -gt 0) {
  Step "Downloading $($toInstall.Count) mod(s) from Modrinth"
  New-Item -ItemType Directory -Force -Path $staging | Out-Null
  foreach ($mod in $toInstall) {
    $tmp = Join-Path $staging $mod.filename
    try { Invoke-WebRequest -UseBasicParsing -Uri $mod.url -OutFile $tmp -Headers @{ "User-Agent" = "av1017/minecraft-modpack" } }
    catch { Fail "Couldn't download $($mod.name): $($_.Exception.Message). Nothing was changed." }
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
$backupDir = Join-Path $MinecraftDir "setup-backups\$stamp"
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
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }

if ($needLoader) {
  New-Item -ItemType Directory -Force -Path (Split-Path $versionFile) | Out-Null
  Copy-Item -LiteralPath $loaderJson -Destination $versionFile -Force
  Ok "Installed Fabric loader version $versionId"
}

if ($needProfile) {
  $now = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.000Z")
  $newProfile = [pscustomobject]@{
    created = $now; icon = $m.profile.icon; lastUsed = $now
    lastVersionId = $versionId; name = $m.profile.name; type = "custom"
  }
  if ($currentProfile) { $profiles.profiles.$profileKey = $newProfile }
  else { $profiles.profiles | Add-Member -NotePropertyName $profileKey -NotePropertyValue $newProfile }
  [System.IO.File]::WriteAllText($profilesPath, ($profiles | ConvertTo-Json -Depth 20), $utf8NoBom)
  $null = [System.IO.File]::ReadAllText($profilesPath) | ConvertFrom-Json
  Ok "Launcher profile saved and launcher_profiles.json still parses"
}

Write-Host "`nSYNC COMPLETE. Choose '$($m.profile.name)' in the launcher and press Play." -ForegroundColor Green
Write-Host "Backup of the previous state: $backupDir"
