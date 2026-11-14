@echo off
rem Download the latest pack (mods.json and friends) before syncing. Never fatal: if Git is missing, this
rem folder isn't a Git copy, or the download fails, the sync just uses the pack already on this PC.
where git >nul 2>nul || (echo Git isn't installed, so syncing the pack as it is on this PC. & exit /b 0)
if not exist "%~dp0..\.git" (echo This folder isn't a Git copy, so syncing the pack as it is on this PC. & exit /b 0)
echo Getting the latest pack...
git -C "%~dp0.." pull --ff-only
if errorlevel 1 echo Couldn't download the latest pack (see above), so syncing the pack as it is on this PC.
echo.
exit /b 0
