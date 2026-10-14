@echo off
setlocal
cd /d "%~dp0"
if not exist "pokeemerald.exe" (
  echo ERRO: pokeemerald.exe nao encontrado nesta pasta.
  pause
  exit /b 1
)
echo Emerald Hybrid LAN - ANFITRIAO
set "PORT="
set /p "PORT=Porta TCP [45680]: "
if not defined PORT set "PORT=45680"
echo Gerando log em lan-host.log
echo Abrindo host LAN na porta %PORT%.
pokeemerald.exe --lan-log "lan-host.log" --lan-host=%PORT%
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo O jogo terminou com erro %RC%. Guarde o arquivo lan-host.log.
  pause
)
exit /b %RC%
