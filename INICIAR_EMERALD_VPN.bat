@echo off
setlocal
cd /d "%~dp0"
rem This wrapper invokes only the local reviewed PowerShell script.
rem ExecutionPolicy Bypass is PROCESS-LOCAL. No administrator elevation.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0INICIAR_EMERALD_VPN.ps1"
if errorlevel 1 (
    echo.
    echo Nao foi possivel iniciar. Confira a mensagem acima e o README_VPN_PTBR.md.
    pause
)
endlocal
