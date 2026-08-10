#define MyAppName "ClimateTest Manager"
#define MyAppVersion "0.6.0"
#define MyAppPublisher "Jhon Cleiton"
#define MyAppExeName "ClimateTestManager.exe"

[Setup]
AppId={{6E8E74D2-9E9E-4CB8-B877-CFEAC5F9C9CF}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ClimateTest Manager
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=ClimateTestManager-Server-Setup-v{#MyAppVersion}
SetupIconFile=..\src\assets\brand\climatetest.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Dirs]
Name: "{localappdata}\ClimateTestManager\Data"

[Files]
Source: "..\dist\ClimateTestManager-v0.6.0\ClimateTestManager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.6.0\ClimateTestServer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.6.0\ClimateTestNotifier.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.6.0\climatetest.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.6.0\LEIA-ME-PRIMEIRO.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.6.0\install_server_tasks.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.6.0\uninstall_server_tasks.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.6.0\documentacao-conformidade\*"; DestDir: "{app}\documentacao-conformidade"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--url http://localhost:8550"; IconFilename: "{app}\climatetest.ico"

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\install_server_tasks.ps1"" -InstallDirectory ""{app}"" -DataDirectory ""{localappdata}\ClimateTestManager\Data"" -Port 8550"; Flags: runhidden waituntilterminated; StatusMsg: "Configurando o servidor seguro na rede local..."
Filename: "{app}\{#MyAppExeName}"; Parameters: "--url http://localhost:8550"; Description: "Abrir o ClimateTest Manager"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\uninstall_server_tasks.ps1"""; Flags: runhidden waituntilterminated
