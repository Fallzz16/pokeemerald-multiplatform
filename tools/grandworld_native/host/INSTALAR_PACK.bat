@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Arraste um pacote ZIP de recursos para cima deste arquivo.
  echo Requer Python 3.12 ou superior instalado.
  pause
  exit /b 1
)
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 tools\pack_manager.py --root mods install "%~1" --enable
) else (
  python tools\pack_manager.py --root mods install "%~1" --enable
)
if errorlevel 1 (
  echo Falha ao validar/instalar pacote. Confira o erro acima.
  pause
  exit /b 1
)
echo Pacote instalado e habilitado. No Style Lab pressione F5 para atualizar.
pause
