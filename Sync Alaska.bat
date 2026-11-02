@echo off
cd /d "%~dp0"
echo Syncing the Alaskan Wilderness mods...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync.ps1" -Pack alaska-fabric
echo.
pause
