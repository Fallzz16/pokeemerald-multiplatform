; Emerald Hybrid M2 EHL8 isolated beta installer — does not overwrite v0.8.2.
Unicode True
!cd ".."
!include "MUI2.nsh"
Name "Emerald Hybrid EHL8 M2 PREVIEW"
OutFile "release\Emerald_Hybrid_EHL8_M2_PREVIEW_INSTALADOR_Windows.exe"
InstallDir "$LOCALAPPDATA\Programs\EmeraldHybridM2Preview"
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
Section "Emerald M2 Preview" SecMain
  SetShellVarContext current
  SetOutPath "$INSTDIR"
  File "payload\EmeraldLauncher.exe"
  File "payload\pokeemerald.exe"
  File "payload\SDL2.dll"
  File "payload\emerald_profilectl.exe"
  File "payload\EmeraldSessionServer.exe"
  File "payload\EHL8_PREVIEW_MODE.txt"
  File "payload\LEIA_PRIMEIRO.txt"
  File "payload\LEIA_QA_PTBR.md"
  File "payload\AI_README.md"
  File "payload\SHA256_COMPONENTES.txt"
  ; Profiles are deliberately isolated from the approved stable install:
  ; %LOCALAPPDATA%\EmeraldHybridEHL8Preview\profiles
  ; NO PORTABLE_MODE marker in installed version.
  WriteUninstaller "$INSTDIR\Desinstalar_EHL8_Preview.exe"
  CreateDirectory "$SMPROGRAMS\Emerald Hybrid EHL8 Preview"
  CreateShortCut "$SMPROGRAMS\Emerald Hybrid EHL8 Preview\Emerald Launcher.lnk" "$INSTDIR\EmeraldLauncher.exe"
  CreateShortCut "$SMPROGRAMS\Emerald Hybrid EHL8 Preview\Desinstalar.lnk" "$INSTDIR\Desinstalar_EHL8_Preview.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EmeraldHybridEHL8Preview" "DisplayName" "Emerald Hybrid EHL8 M2 PREVIEW"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EmeraldHybridEHL8Preview" "UninstallString" '"$INSTDIR\Desinstalar_EHL8_Preview.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EmeraldHybridEHL8Preview" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EmeraldHybridEHL8Preview" "NoModify" 1
SectionEnd
Section "Uninstall"
  SetShellVarContext current
  Delete "$SMPROGRAMS\Emerald Hybrid EHL8 Preview\Emerald Launcher.lnk"
  Delete "$SMPROGRAMS\Emerald Hybrid EHL8 Preview\Desinstalar.lnk"
  RMDir "$SMPROGRAMS\Emerald Hybrid EHL8 Preview"
  Delete "$INSTDIR\EmeraldLauncher.exe"
  Delete "$INSTDIR\pokeemerald.exe"
  Delete "$INSTDIR\SDL2.dll"
  Delete "$INSTDIR\emerald_profilectl.exe"
  Delete "$INSTDIR\EmeraldSessionServer.exe"
  Delete "$INSTDIR\EHL8_PREVIEW_MODE.txt"
  Delete "$INSTDIR\LEIA_PRIMEIRO.txt"
  Delete "$INSTDIR\LEIA_QA_PTBR.md"
  Delete "$INSTDIR\AI_README.md"
  Delete "$INSTDIR\SHA256_COMPONENTES.txt"
  Delete "$INSTDIR\Desinstalar_EHL8_Preview.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\EmeraldHybridEHL8Preview"
  ; Preserve local M2 preview saves and logs:
  ; $LOCALAPPDATA\EmeraldHybridEHL8Preview\profiles
  ; $LOCALAPPDATA\EmeraldHybridEHL8Preview\logs
  ; Never touch the stable EmeraldHybrid user profile folder.
SectionEnd
