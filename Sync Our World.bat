@echo off
cd /d "%~dp0"
echo Syncing the Our World mods...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync.ps1" -Pack our-world
echo.
pause
