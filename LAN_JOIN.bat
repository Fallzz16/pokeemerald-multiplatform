@echo off
setlocal
cd /d "%~dp0"
echo Emerald Hybrid LAN - JOIN
echo Use o IPv4 local do PC anfitriao (ipconfig).
set "HOST="
set /p "HOST=IP local do anfitriao: "
if not defined HOST (
  echo IP obrigatorio.
  pause
  exit /b 1
)
set "PORT="
set /p "PORT=Porta TCP [45680]: "
if not defined PORT set "PORT=45680"
pokeemerald.exe --lan-client=%HOST%:%PORT%
if errorlevel 1 pause
