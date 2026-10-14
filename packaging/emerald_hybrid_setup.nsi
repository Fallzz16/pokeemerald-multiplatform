; Emerald Hybrid v0.8.2 - PER-USER installation.
; This installer bundles only reviewed Windows binaries.
; Saves remain outside the installed app in %LOCALAPPDATA%\EmeraldHybrid.
Unicode True
!include "MUI2.nsh"
Name "Emerald Hybrid v0.8.2 (Experimental)"
OutFile "release\Emerald_Hybrid_v0802_INSTALADOR_Windows.exe"
InstallDir "$LOCALAPPDATA\Programs\EmeraldHybrid"
RequestExecutionLevel user
SetCompressor /SOLID lzma
ShowInstDetails show
ShowUninstDetails show
!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "PortugueseBR"

Section "Emerald Hybrid" SecMain
  SetShellVarContext current
  SetOutPath "$INSTDIR"
  File "payload\EmeraldLauncher.exe"
  File "payload\pokeemerald.exe"
  File "payload\SDL2.dll"
  File "payload\emerald_profilectl.exe"
  File "payload\LEIA_PRIMEIRO.txt"
  ; IMPORTANT: Never ship PORTABLE_MODE.txt in the installed version.
  ; Installer profiles stay in %LOCALAPPDATA%\EmeraldHybrid\profiles,
  ; outside $INSTDIR. They will not be removed by uninstall.
  WriteUninstaller "$INSTDIR\Desinstalar_Emerald_Hybrid.exe"
  CreateDirectory "$SMPROGRAMS\Emerald Hybrid"
  CreateShortCut "$SMPROGRAMS\Emerald Hybrid\Emerald Launcher.lnk" "$INSTDIR\EmeraldLauncher.exe"
  CreateShortCut "$SMPROGRAMS\Emerald Hybrid\Desinstalar.lnk" "$INSTDIR\Desinstalar_Emerald_Hybrid.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EmeraldHybridExperimental" "DisplayName" "Emerald Hybrid v0.8.2 (Experimental)"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EmeraldHybridExperimental" "UninstallString" '"$INSTDIR\Desinstalar_Emerald_Hybrid.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EmeraldHybridExperimental" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EmeraldHybridExperimental" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EmeraldHybridExperimental" "NoRepair" 1
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  Delete "$SMPROGRAMS\Emerald Hybrid\Emerald Launcher.lnk"
  Delete "$SMPROGRAMS\Emerald Hybrid\Desinstalar.lnk"
  RMDir "$SMPROGRAMS\Emerald Hybrid"
  Delete "$INSTDIR\EmeraldLauncher.exe"
  Delete "$INSTDIR\pokeemerald.exe"
  Delete "$INSTDIR\SDL2.dll"
  Delete "$INSTDIR\emerald_profilectl.exe"
  Delete "$INSTDIR\LEIA_PRIMEIRO.txt"
  Delete "$INSTDIR\Desinstalar_Emerald_Hybrid.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EmeraldHybridExperimental"
  ; Deliberately preserve:
  ; %LOCALAPPDATA%\EmeraldHybrid\profiles (local user saves)
  ; %LOCALAPPDATA%\EmeraldHybrid\logs
SectionEnd
