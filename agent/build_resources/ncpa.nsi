!include "MUI.nsh"
!include "nsDialogs.nsh"
!include FileFunc.nsh
!insertmacro GetParameters
!insertmacro GetOptions

!define UNINST_KEY \
  "Software\Microsoft\Windows\CurrentVersion\Uninstall\NCPA"
; ...
!define MULTIUSER_INSTALLMODE_COMMANDLINE
; ...
!include "MultiUser.nsh"

!define CONFIG_INI "$INSTDIR\Config.ini"

;The name of the installer
Name "NCPA Installer"

;The file to write
OutFile "NCPA_Installer.exe"
 
;The default installation directory
InstallDir $PROGRAMFILES32\Nagios\NCPA

;request admin execution
RequestExecutionLevel admin

;Settings
ShowInstDetails show

LoadLanguageFile "${NSISDIR}\Contrib\Language files\English.nlf"

;Order of pages
!define MUI_LANGUAGEFILE_DEFAULT "ENGLISH"
LangString MUI_INNERTEXT_LICENSE_BOTTOM "ENGLISH" "Nagios Software License 1.3"
LangString MUI_TEXT_LICENSE_TITLE "ENGLISH" "Nagios Enterprises LLC"
LangString MUI_TEXT_LICENSE_SUBTITLE "ENGLISH" "NCPA for Windows"
LangString MUI_INNERTEXT_LICENSE_TOP "ENGLISH" "Software License Agreement"
!insertmacro MUI_PAGE_LICENSE ".\NCPA\build_resources\NagiosSoftwareLicense.txt"
# Page components
Page custom SetCustom
Page directory
Page instfiles

Function .onInit

  InitPluginsDir
	!insertmacro INSTALLOPTIONS_EXTRACT_AS "NCPA\build_resources\field.ini" "field.ini"
	
	${GetParameters} $R0
	${GetParameters} $R1
	${GetParameters} $R2
	${GetParameters} $R3
	
  ClearErrors
  ${GetOptions} $R0 /NRDP= $0
	${GetOptions} $R1 /TOKEN= $1
	${GetOptions} $R2 /CONFIG= $2
	${GetOptions} $R3 /HOST= $3

FunctionEnd

Function SetCustom

  ;Display the InstallOptions dialog
	!insertmacro INSTALLOPTIONS_DISPLAY "field.ini"
	!define CHK_PROXYSETTINGS "Field 6"
	!insertmacro INSTALLOPTIONS_READ $0 "field.ini" "Field 1" "State"
	!insertmacro INSTALLOPTIONS_READ $1 "field.ini" "Field 2" "State"
	!insertmacro INSTALLOPTIONS_READ $2 "field.ini" "Field 3" "State"
	!insertmacro INSTALLOPTIONS_READ $3 "field.ini" "Field 4" "State"

FunctionEnd

Section # "Create Config.ini"
	
	SetOutPath $INSTDIR

	File /r .\NCPA\*.*

	WriteINIStr $INSTDIR\etc\ncpa.cfg nrds "CONFIG_VERSION" "0"
	WriteINIStr $INSTDIR\etc\ncpa.cfg nrds "CONFIG_NAME" "$2"
	WriteINIStr $INSTDIR\etc\ncpa.cfg nrds "URL" "$0"
    WriteINIStr $INSTDIR\etc\ncpa.cfg nrdp "parent" "$0"
	WriteINIStr $INSTDIR\etc\ncpa.cfg nrds "TOKEN" "$1"
    WriteINIStr $INSTDIR\etc\ncpa.cfg nrdp "token" "$1"
    WriteINIStr $INSTDIR\etc\ncpa.cfg api "community_string" "$1"
	WriteINIStr $INSTDIR\etc\ncpa.cfg nrds "PLUGIN_DIR" "plugins/"
	WriteINIStr $INSTDIR\etc\ncpa.cfg nrds "UPDATE_CONFIG" "1"
	WriteINIStr $INSTDIR\etc\ncpa.cfg nrds "UPDATE_PLUGINS" "1"
	
	WriteINIStr $INSTDIR\etc\ncpa.cfg nrdp "hostname" "$3"

SectionEnd


Section ""
  ; ...
 
  WriteRegStr SHCTX "${UNINST_KEY}" "DisplayName" "NCPA"
  WriteRegStr SHCTX "${UNINST_KEY}" "UninstallString" \
    "$\"$INSTDIR\uninstall.exe$\" /$MultiUser.InstallMode"
  WriteRegStr SHCTX "${UNINST_KEY}" "QuietUninstallString" \
    "$\"$INSTDIR\uninstall.exe$\" /$MultiUser.InstallMode /S"
 
  WriteUninstaller $INSTDIR\uninstall.exe
  
  ReadEnvStr $9 COMSPEC
  nsExec::Exec '$9 /c "$INSTDIR\ncpa_listener.exe" --install ncpalistener'
  nsExec::Exec '$9 /c "$INSTDIR\ncpa_passive.exe" --install ncpapassive'
 
  ; ...
SectionEnd

Section "Uninstall"

    Delete "$INSTDIR\uninstall.exe"
    
	ReadEnvStr $9 COMSPEC
	
	nsExec::Exec '$9 /c "$INSTDIR\ncpa_listener.exe" --uninstall ncpalistener'
    nsExec::Exec '$9 /c "$INSTDIR\ncpa_passive.exe" --uninstall ncpapassive'
    
    DeleteRegKey SHCTX "${UNINST_KEY}"
    
	RMDir /r "$INSTDIR"
	
SectionEnd