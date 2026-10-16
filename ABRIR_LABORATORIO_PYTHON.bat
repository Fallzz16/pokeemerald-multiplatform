@echo off
cd /d "%~dp0"
if not exist "pokeemerald.exe" (
  echo ERRO: extraia ESTE conteudo na pasta do Emerald M2 Preview completa.
  echo Devem estar ao lado: pokeemerald.exe, SDL2.dll, emerald_profilectl.exe, EmeraldSessionServer.exe
  pause
  exit /b 1
)
where pythonw >nul 2>&1
if errorlevel 1 (
  echo Python 3 com Tkinter nao encontrado. Instale Python 3.12+ ou utilize o executavel compilado pelo CI.
  pause
  exit /b 1
)
start "" pythonw "%~dp0tools\emerald_qa_lab.py"
