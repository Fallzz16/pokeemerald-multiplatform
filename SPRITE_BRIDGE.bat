@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")
%PY% -c "import PIL" >nul 2>nul || %PY% -m pip install Pillow
if errorlevel 1 (
  echo Pillow was not installed. No sprites changed.
  pause
  exit /b 2
)
echo.
echo === Emerald Sprite Bridge v0.7 ===
echo DRY RUN is the default, to prevent accidental file changes.
echo Example: SPRITE_BRIDGE.bat --source platinum --species pikachu gardevoir
echo To import: append --apply (creates backups automatically).
echo.
%PY% tools\sprite_bridge.py %*
if errorlevel 1 (
  echo.
  echo Import blocked / failed. Read the message above.
  pause
  exit /b 1
)
pause
