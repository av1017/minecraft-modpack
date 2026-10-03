@echo off
cd /d "%~dp0"
echo Syncing Minecraft mods with mods.json...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync.ps1"
echo.
pause
