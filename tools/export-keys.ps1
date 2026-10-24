<#
  Saves the host PC's key bindings as a pack's key layout (packs\<pack>\keys.txt).
  Run it after changing keys in game and closing Minecraft, then commit keys.txt.
  sync.ps1 applies the layout: keys a PC doesn't have yet always get it, and
  -MatchKeys (or a first-time setup) sets every key to it.

    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\export-keys.ps1 -Pack cobblemon
#>
param([Parameter(Mandatory = $true)][string]$Pack, [string]$MinecraftDir = (Join-Path $env:APPDATA ".minecraft"))
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$m = Get-Content -Raw -LiteralPath (Join-Path $repo "packs\$Pack\mods.json") | ConvertFrom-Json
$gameDir = $MinecraftDir
if ($m.PSObject.Properties.Name -contains "game_dir" -and $m.game_dir) { $gameDir = Join-Path (Split-Path -Parent $MinecraftDir) $m.game_dir }
$opts = Join-Path $gameDir "options.txt"
if (-not (Test-Path -LiteralPath $opts)) { throw "No options.txt at $opts. Launch the pack once first." }
$keys = @([System.IO.File]::ReadAllLines($opts) | Where-Object { $_ -match '^key_[^:]+:.+$' } | Sort-Object)
$out = Join-Path $repo "packs\$Pack\keys.txt"
[System.IO.File]::WriteAllText($out, (($keys -join "`n") + "`n"), (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Saved $($keys.Count) key bindings from $opts to $out"
