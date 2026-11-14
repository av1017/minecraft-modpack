@echo off
cd /d "%~dp0"
call "%~dp0tools\pull-latest.cmd"
echo Syncing the Cobblemon mods...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync.ps1" -Pack cobblemon
echo.
pause
