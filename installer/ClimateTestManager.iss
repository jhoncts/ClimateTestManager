#define MyAppName "ClimateTest Manager"
#define MyAppVersion "0.7.0"
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
Source: "..\dist\ClimateTestManager-v0.7.0\ClimateTestManager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.7.0\ClimateTestServer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.7.0\ClimateTestNotifier.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.7.0\climatetest.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.7.0\LEIA-ME-PRIMEIRO.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.7.0\install_server_tasks.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.7.0\uninstall_server_tasks.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.7.0\documentacao-conformidade\*"; DestDir: "{app}\documentacao-conformidade"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--url http://localhost:8550"; IconFilename: "{app}\climatetest.ico"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--url http://localhost:8550"; IconFilename: "{app}\climatetest.ico"
Name: "{autoprograms}\ClimateTest Manager - Diagnóstico"; Filename: "{sys}\explorer.exe"; Parameters: """{commonappdata}\ClimateTestManager\Logs"""; IconFilename: "{app}\climatetest.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--url http://localhost:8550"; Description: "Abrir o ClimateTest Manager em sua janela"; Flags: nowait postinstall skipifsilent; Check: ServerReady

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

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  PowerShellPath: String;
  Params: String;
begin
  Result := '';
  NeedsRestart := False;
  WizardForm.StatusLabel.Caption := 'Preparando atualização e encerrando a versão anterior...';

  PowerShellPath := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
  Params := '-NoProfile -ExecutionPolicy Bypass -Command "& {' +
    ' $ErrorActionPreference = ''SilentlyContinue'';' +
    ' $tasks = @(''ClimateTestManager-Server'',''ClimateTestManager-Background'',''ClimateTestManager-Notifications'');' +
    ' foreach ($task in $tasks) {' +
    '   Stop-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue;' +
    '   Disable-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue | Out-Null;' +
    ' };' +
    ' & taskkill.exe /F /T /IM ClimateTestServer.exe 2>$null | Out-Null;' +
    ' & taskkill.exe /F /T /IM ClimateTestNotifier.exe 2>$null | Out-Null;' +
    ' & taskkill.exe /F /T /IM ClimateTestManager.exe 2>$null | Out-Null;' +
    ' for ($i = 0; $i -lt 20; $i++) {' +
    '   $running = Get-Process -Name ClimateTestServer,ClimateTestNotifier,ClimateTestManager -ErrorAction SilentlyContinue;' +
    '   if (-not $running) { exit 0 };' +
    '   Start-Sleep -Milliseconds 500;' +
    ' };' +
    ' exit 31' +
    '}"';

  if not Exec(PowerShellPath, Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    Result := 'O instalador não conseguiu preparar a atualização. Feche o ClimateTest Manager e tente novamente. Código CTM-UPD-001.';
    Exit;
  end;

  if ResultCode <> 0 then
  begin
    Result := 'A versão anterior do ClimateTest Manager continua em execução e não pôde ser encerrada automaticamente. Código CTM-UPD-' + IntToStr(ResultCode) + '. Não ignore arquivos: cancele e informe este código.';
  end;
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
        'Clique em Concluir para abrir a janela do ClimateTest Manager.';
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
