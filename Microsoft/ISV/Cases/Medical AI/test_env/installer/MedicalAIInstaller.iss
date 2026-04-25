#define MyAppName "Medical AI Local Runtime"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Medical AI"
#define MyAppExeName "MedicalAI-Installer.exe"

#ifndef SourceDir
  #define SourceDir "_work\package"
#endif

#ifndef OutputDir
  #define OutputDir "output"
#endif

[Setup]
AppId={{D386683B-8593-4E79-B2CB-1EE2D432108A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={commonappdata}\MedicalAI
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=MedicalAI-Installer
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
SetupLogging=yes
Uninstallable=yes

[Files]
Source: "{#SourceDir}\payload\*"; DestDir: "{app}\payload"; Flags: recursesubdirs createallsubdirs ignoreversion

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\payload\Install-MedicalAI.ps1"" -InstallRoot ""{app}"""; Flags: runhidden waituntilterminated

[UninstallDelete]
Type: filesandordirs; Name: "{app}\payload"
