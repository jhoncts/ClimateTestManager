#define MyAppName "ClimateTest Manager"
#define MyAppVersion "0.6.2"
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
SetupLogging=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Dirs]
Name: "{commonappdata}\ClimateTestManager"
Name: "{commonappdata}\ClimateTestManager\Data"
Name: "{commonappdata}\ClimateTestManager\Logs"
Name: "{commonappdata}\ClimateTestManager\Backups"

[Files]
Source: "..\dist\ClimateTestManager-v0.6.2\ClimateTestManager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.6.2\ClimateTestServer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.6.2\ClimateTestNotifier.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.6.2\climatetest.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.6.2\LEIA-ME-PRIMEIRO.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.6.2\install_server_tasks.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.6.2\uninstall_server_tasks.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.6.2\documentacao-conformidade\*"; DestDir: "{app}\documentacao-conformidade"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--url http://localhost:8550"; IconFilename: "{app}\climatetest.ico"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--url http://localhost:8550"; IconFilename: "{app}\climatetest.ico"
Name: "{autoprograms}\ClimateTest Manager - Diagnóstico"; Filename: "{sys}\explorer.exe"; Parameters: """{commonappdata}\ClimateTestManager\Logs"""; IconFilename: "{app}\climatetest.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--url http://localhost:8550"; Description: "Abrir o ClimateTest Manager"; Flags: nowait postinstall skipifsilent; Check: ServerReady

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\uninstall_server_tasks.ps1"""; Flags: runhidden waituntilterminated

[Code]
var
  ServerConfigured: Boolean;
  ServerConfigExitCode: Integer;

function ServerReady(): Boolean;
begin
  Result := ServerConfigured;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Params: String;
  PowerShellPath: String;
begin
  if CurStep = ssPostInstall then
  begin
    ServerConfigured := False;
    ServerConfigExitCode := -1;
    WizardForm.StatusLabel.Caption := 'Configurando e verificando o servidor central...';

    PowerShellPath := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
    Params := '-NoProfile -ExecutionPolicy Bypass -File "' +
      ExpandConstant('{app}\install_server_tasks.ps1') +
      '" -InstallDirectory "' + ExpandConstant('{app}') +
      '" -DataDirectory "' +
      ExpandConstant('{commonappdata}\ClimateTestManager\Data') +
      '" -Port 8550';

    if Exec(PowerShellPath, Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    begin
      ServerConfigExitCode := ResultCode;
      ServerConfigured := ResultCode = 0;
    end;
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
var
  LogDirectory: String;
begin
  if CurPageID = wpFinished then
  begin
    LogDirectory := ExpandConstant('{commonappdata}\ClimateTestManager\Logs');
    if ServerConfigured then
    begin
      WizardForm.FinishedHeadingLabel.Caption := 'ClimateTest Manager pronto para uso';
      WizardForm.FinishedLabel.Caption :=
        'O servidor central foi instalado, iniciado e verificado com sucesso.' + #13#10 + #13#10 +
        'Clique em Concluir para abrir o ClimateTest Manager.';
    end
    else
    begin
      WizardForm.FinishedHeadingLabel.Caption := 'A instalação precisa de atenção';
      WizardForm.FinishedLabel.Caption :=
        'Os arquivos foram instalados e seus dados foram preservados, mas o servidor central ' +
        'não conseguiu iniciar.' + #13#10 + #13#10 +
        'Código de diagnóstico: CTM-SRV-' + IntToStr(ServerConfigExitCode) + #13#10 +
        'Diagnóstico salvo em: ' + LogDirectory + #13#10 + #13#10 +
        'Não é necessário apagar banco de dados nem reinstalar o Windows. O registro acima ' +
        'indica exatamente a etapa que precisa ser corrigida.';
    end;
  end;
end;
