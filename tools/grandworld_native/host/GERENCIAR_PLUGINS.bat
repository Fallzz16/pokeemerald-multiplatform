@echo off
setlocal
cd /d "%~dp0"
if not exist "tools\plugin_ui.py" (
  echo Gerenciador de plugins nao encontrado.
  pause
  exit /b 1
)
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 tools\plugin_ui.py --mods mods --lab gw_theme_lab.exe
) else (
  python tools\plugin_ui.py --mods mods --lab gw_theme_lab.exe
)
if errorlevel 1 (
  echo Nao foi possivel abrir o gerenciador.
  echo Necessario Python 3 com Tkinter instalado.
  pause
  exit /b 1
)
