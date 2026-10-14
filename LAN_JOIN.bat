@echo off
setlocal
cd /d "%~dp0"
if not exist "pokeemerald.exe" (
  echo ERRO: pokeemerald.exe nao encontrado nesta pasta.
  pause
  exit /b 1
)
echo Emerald Hybrid LAN - CLIENTE
echo Use o IPv4 local do PC anfitriao ^(comando ipconfig^).
set "HOST="
set /p "HOST=IPv4 local do anfitriao: "
if not defined HOST (
  echo IP obrigatorio.
  pause
  exit /b 1
)
set "PORT="
set /p "PORT=Porta TCP [45680]: "
if not defined PORT set "PORT=45680"
echo Gerando log em lan-cliente.log
pokeemerald.exe --lan-log "lan-cliente.log" --lan-client=%HOST%:%PORT%
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo O jogo terminou com erro %RC%. Guarde o arquivo lan-cliente.log.
  pause
)
exit /b %RC%
