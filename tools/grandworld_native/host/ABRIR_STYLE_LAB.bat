@echo off
setlocal
cd /d "%~dp0"
if not exist "gw_theme_lab.exe" (
  echo Executavel gw_theme_lab.exe nao encontrado.
  pause
  exit /b 1
)
gw_theme_lab.exe --mods mods
if errorlevel 1 (
  echo O aplicativo encerrou com erro. Confira as DLLs deste pacote.
  pause
  exit /b 1
)
