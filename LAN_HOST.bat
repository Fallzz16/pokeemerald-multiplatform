@echo off
setlocal
cd /d "%~dp0"
echo Emerald Hybrid LAN - HOST
set "PORT="
set /p "PORT=Porta TCP [45680]: "
if not defined PORT set "PORT=45680"
echo Abrindo host LAN na porta %PORT%.
pokeemerald.exe --lan-host=%PORT%
if errorlevel 1 pause
