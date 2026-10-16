@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Python Launcher (py) nao instalado. Instale Python 3.12/3.13 para Windows.
  pause
  exit /b 1
)
if not exist "pokeemerald.exe" (
  echo [ERRO] Coloque estes arquivos na pasta COMPLETA do Emerald M2 Preview antes.
  pause
  exit /b 1
)
py -3 -m venv "%~dp0.qa_builder"
if errorlevel 1 goto fail
"%~dp0.qa_builder\Scripts\python.exe" -m pip install --disable-pip-version-check pyinstaller==6.16.0
if errorlevel 1 goto fail
"%~dp0.qa_builder\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name EmeraldQALab tools\emerald_qa_lab.py
if errorlevel 1 goto fail
"%~dp0.qa_builder\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --console --name EmeraldQABots tools\emerald_qa_bots.py
if errorlevel 1 goto fail
copy /Y "dist\EmeraldQALab.exe" "%~dp0EmeraldQALab.exe" >nul
if errorlevel 1 goto fail
copy /Y "dist\EmeraldQABots.exe" "%~dp0EmeraldQABots.exe" >nul
if errorlevel 1 goto fail
echo.
echo [OK] EmeraldQALab.exe + EmeraldQABots.exe criados. Abra o Lab sem CMD.
pause
exit /b 0
:fail
echo [ERRO] Compilacao nao concluida. Veja as mensagens anteriores.
pause
exit /b 1
