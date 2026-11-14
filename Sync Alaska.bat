@echo off
cd /d "%~dp0"
call "%~dp0tools\pull-latest.cmd"
echo Syncing the Alaskan Wilderness mods...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync.ps1" -Pack alaska-fabric
echo.
pause
