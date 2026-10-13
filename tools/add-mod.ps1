<#
  Adds (or updates) mods in mods.json from Modrinth, including required dependencies.
  Only picks releases built for this pack's loader and Minecraft version.

    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\add-mod.ps1 -Pack our-world -Slug sodium -DryRun
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\add-mod.ps1 -Pack cobblemon -Slug sodium,lithium

  -Pack        Which pack to edit (a folder name under packs\). Default: our-world.
  -Slug        One or more Modrinth project slugs (the name in the URL: modrinth.com/mod/<slug>).
  -DryRun      Show what would change without writing mods.json.
  -AllowBeta   Accept beta/alpha builds when no release exists.

  This only edits mods.json. Afterwards: run sync.ps1, test in-game, then commit and push.
#>
param(
  [string]$Pack = "our-world",
  [Parameter(Mandatory = $true)][string[]]$Slug,
  [switch]$DryRun,
  [switch]$AllowBeta
)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
# "powershell -File" passes "-Slug a,b" as one string; split it so both forms work.
$Slug = @($Slug | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$manifestPath = Join-Path $repo "packs\$Pack\mods.json"
if (-not (Test-Path $manifestPath)) { Write-Host "STOPPED: No pack named '$Pack' (expected $manifestPath)." -ForegroundColor Red; exit 1 }
$headers = @{ "User-Agent" = "av1017/minecraft-modpack" }
$api = "https://api.modrinth.com/v2"

function Fail($msg) { Write-Host "`nSTOPPED: $msg" -ForegroundColor Red; exit 1 }
function Enc($s) { [Uri]::EscapeDataString($s) }

# Minimal JSON writer that matches the repo's 2-space format and doesn't escape apostrophes.
function Write-JsonValue($v, [int]$level) {
  $pad = "  " * $level; $pad1 = "  " * ($level + 1)
  if ($null -eq $v) { return "null" }
  if ($v -is [bool]) { if ($v) { return "true" } else { return "false" } }
  if ($v -is [int] -or $v -is [long] -or $v -is [double] -or $v -is [decimal]) { return [string]$v }
  if ($v -is [string]) {
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append('"')
    foreach ($ch in $v.ToCharArray()) {
      switch ($ch) {
        '"'  { [void]$sb.Append('\"') }
        '\'  { [void]$sb.Append('\\') }
        "`n" { [void]$sb.Append('\n') }
        "`r" { [void]$sb.Append('\r') }
        "`t" { [void]$sb.Append('\t') }
        default { if ([int]$ch -lt 32) { [void]$sb.Append(('\u{0:x4}' -f [int]$ch)) } else { [void]$sb.Append($ch) } }
      }
    }
    [void]$sb.Append('"'); return $sb.ToString()
  }
  if ($v -is [System.Collections.IEnumerable] -and -not ($v -is [System.Management.Automation.PSCustomObject])) {
    $items = @($v)
    if ($items.Count -eq 0) { return "[]" }
    $parts = foreach ($i in $items) { $pad1 + (Write-JsonValue $i ($level + 1)) }
    return "[`n" + ($parts -join ",`n") + "`n$pad]"
  }
  $props = @($v.PSObject.Properties)
  if ($props.Count -eq 0) { return "{}" }
  $parts = foreach ($p in $props) { $pad1 + '"' + $p.Name + '": ' + (Write-JsonValue $p.Value ($level + 1)) }
  return "{`n" + ($parts -join ",`n") + "`n$pad}"
}

$m = [System.IO.File]::ReadAllText($manifestPath) | ConvertFrom-Json
$mc = $m.minecraft
$loader = $m.loader.type
$mods = New-Object System.Collections.ArrayList
foreach ($x in @($m.mods)) { [void]$mods.Add($x) }

$changes = New-Object System.Collections.ArrayList
$seen = @{}

function Resolve-Mod([string]$projectRef, [string]$pinnedVersionId, [bool]$isDependency) {
  $project = Invoke-RestMethod -Uri "$api/project/$(Enc $projectRef)" -Headers $headers
  if ($seen.ContainsKey($project.id)) { return }
  $seen[$project.id] = $true

  # Dependencies already in the pack stay at their current version; only requested mods get updated.
  if ($isDependency) {
    foreach ($x in $mods) {
      if ($x.project_id -eq $project.id) {
        Write-Host "   keep     $($project.title) $($x.version) (already in pack)" -ForegroundColor DarkGray
        return
      }
    }
  }

  if ($pinnedVersionId) {
    $version = Invoke-RestMethod -Uri "$api/version/$(Enc $pinnedVersionId)" -Headers $headers
  } else {
    $q = "loaders=" + (Enc ('["' + $loader + '"]')) + "&game_versions=" + (Enc ('["' + $mc + '"]'))
    # Windows PowerShell 5.1 emits a JSON array as ONE pipeline object; unroll it explicitly.
    $raw = Invoke-RestMethod -Uri "$api/project/$($project.id)/version?$q" -Headers $headers
    $versions = New-Object System.Collections.ArrayList
    foreach ($v in $raw) { [void]$versions.Add($v) }
    $version = $null
    foreach ($v in $versions) { if ($v.version_type -eq "release") { $version = $v; break } }
    if (-not $version -and $AllowBeta -and $versions.Count -gt 0) { $version = $versions[0] }
    if (-not $version) { Fail "$($project.title) has no $loader release for Minecraft $mc. (Use -AllowBeta to consider beta builds.)" }
  }
  $file = @($version.files) | Where-Object { $_.primary } | Select-Object -First 1
  if (-not $file) { $file = @($version.files)[0] }

  $side = "both"; if ($project.server_side -eq "unsupported") { $side = "client" }
  $entry = [pscustomobject][ordered]@{
    name = $project.title; slug = $project.slug; project_id = $project.id; version_id = $version.id
    version = $version.version_number; filename = $file.filename; url = $file.url
    sha1 = $file.hashes.sha1; side = $side
  }

  $existing = $null; $idx = -1
  for ($i = 0; $i -lt $mods.Count; $i++) { if ($mods[$i].project_id -eq $project.id) { $existing = $mods[$i]; $idx = $i } }
  if ($existing -and $existing.version_id -eq $version.id) {
    Write-Host "   current  $($project.title) $($version.version_number)" -ForegroundColor DarkGray
  } elseif ($existing) {
    $mods[$idx] = $entry
    [void]$changes.Add("UPDATE $($project.title): $($existing.version) -> $($version.version_number)")
  } else {
    [void]$mods.Add($entry)
    [void]$changes.Add("ADD    $($project.title) $($version.version_number) ($side)")
  }

  foreach ($dep in $version.dependencies) {
    if ($dep.dependency_type -ne "required") { continue }
    if ($dep.project_id) { Resolve-Mod $dep.project_id $null $true }
    elseif ($dep.version_id) {
      $dv = Invoke-RestMethod -Uri "$api/version/$(Enc $dep.version_id)" -Headers $headers
      Resolve-Mod $dv.project_id $dep.version_id $true
    }
  }
}

Write-Host "Resolving for $loader / Minecraft $mc ..."
foreach ($s in $Slug) {
  try { Resolve-Mod $s $null $false }
  catch { Fail "Couldn't look up '$s' on Modrinth: $($_.Exception.Message)" }
}

if ($changes.Count -eq 0) { Write-Host "`nNo changes: everything requested is already current." -ForegroundColor Green; exit 0 }
Write-Host ""
foreach ($c in $changes) { Write-Host "   $c" -ForegroundColor Yellow }

if ($DryRun) { Write-Host "`nDRY RUN: mods.json not written." -ForegroundColor Yellow; exit 0 }

$sorted = @($mods | Sort-Object @{ Expression = { if ($_.side -eq "both") { 0 } else { 1 } } }, @{ Expression = { $_.name.ToLower() } })
$m.mods = $sorted
[System.IO.File]::WriteAllText($manifestPath, (Write-JsonValue $m 0) + "`n", (New-Object System.Text.UTF8Encoding($false)))
$null = [System.IO.File]::ReadAllText($manifestPath) | ConvertFrom-Json
Write-Host "`nmods.json updated. Next: run sync.ps1, test in-game, then commit and push." -ForegroundColor Green
