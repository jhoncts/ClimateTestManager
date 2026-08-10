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
OutputBaseFilename=ClimateTestManager-Setup-v{#MyAppVersion}
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
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\climatetest.ico"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\climatetest.ico"
Name: "{autoprograms}\ClimateTest Manager - Diagnóstico"; Filename: "{sys}\explorer.exe"; Parameters: """{commonappdata}\ClimateTestManager\Logs"""; IconFilename: "{app}\climatetest.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir o ClimateTest Manager"; Flags: nowait postinstall skipifsilent; Check: ShouldLaunchApplication

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\uninstall_server_tasks.ps1"""; Flags: runhidden waituntilterminated; Check: IsServerModeInstall; RunOnceId: "ClimateTestManagerServerCleanup"

[Code]
var
  RolePage: TInputOptionWizardPage;
  AddressPage: TInputQueryWizardPage;
  ExistingServerInstall: Boolean;
  InstallAsServer: Boolean;
  ServerConfigured: Boolean;
  ServerConfigExitCode: Integer;
  ClientReachable: Boolean;
  ClientConfigExitCode: Integer;
  ConfiguredServerUrl: String;

function ReadExistingServerUrl(): String;
var
  Value: AnsiString;
begin
  Result := '';
  if LoadStringFromFile(
    ExpandConstant('{commonappdata}\ClimateTestManager\server.url'),
    Value
  ) then
    Result := Trim(String(Value));
end;

function RequestedRole(): String;
begin
  Result := Lowercase(Trim(ExpandConstant('{param:ROLE|}')));
end;

function RequestedServerAddress(): String;
begin
  Result := Trim(ExpandConstant('{param:SERVERADDRESS|}'));
end;

function SelectedServerMode(): Boolean;
var
  Role: String;
begin
  Role := RequestedRole();
  if Role = 'server' then
  begin
    Result := True;
    Exit;
  end;
  if Role = 'client' then
  begin
    Result := False;
    Exit;
  end;
  Result := RolePage.SelectedValueIndex = 0;
end;

function NormalizeServerAddress(Value: String): String;
var
  Work: String;
  Rest: String;
  SchemePos: Integer;
  SlashPos: Integer;
begin
  Work := Trim(Value);
  while (Length(Work) > 0) and (Work[Length(Work)] = '/') do
    Delete(Work, Length(Work), 1);

  if Pos('://', Work) = 0 then
    Work := 'http://' + Work;

  SchemePos := Pos('://', Work);
  Rest := Copy(Work, SchemePos + 3, Length(Work));
  SlashPos := Pos('/', Rest);
  if SlashPos > 0 then
  begin
    Rest := Copy(Rest, 1, SlashPos - 1);
    Work := Copy(Work, 1, SchemePos + 2) + Rest;
  end;

  if Pos(':', Rest) = 0 then
    Work := Work + ':8550';

  Result := Work;
end;

function CurrentServerUrl(): String;
var
  Address: String;
begin
  if SelectedServerMode() then
  begin
    Result := 'http://localhost:8550';
    Exit;
  end;

  Address := RequestedServerAddress();
  if Address = '' then
    Address := AddressPage.Values[0];
  Result := NormalizeServerAddress(Address);
end;

procedure InitializeWizard();
var
  ExistingUrl: String;
  Role: String;
begin
  { Não expanda {app} aqui: InitializeWizard ocorre antes da seleção definitiva do diretório. }
  ExistingServerInstall :=
    FileExists(ExpandConstant('{commonappdata}\ClimateTestManager\Data\climatetest_manager.db')) or
    FileExists(ExpandConstant('{commonappdata}\ClimateTestManager\server-mode.marker'));
  ExistingUrl := ReadExistingServerUrl();
  Role := RequestedRole();

  RolePage := CreateInputOptionPage(
    wpSelectDir,
    'Tipo de instalação',
    'Como este computador será usado?',
    'Use o mesmo instalador em todas as máquinas. Escolha uma opção e clique em Avançar.',
    True,
    False
  );
  RolePage.Add('Servidor central - guarda os dados e atende as demais máquinas');
  RolePage.Add('Estação de trabalho - conecta ao servidor central');

  if Role = 'server' then
    RolePage.SelectedValueIndex := 0
  else if Role = 'client' then
    RolePage.SelectedValueIndex := 1
  else if ExistingServerInstall or (Lowercase(ExistingUrl) = 'http://localhost:8550') then
    RolePage.SelectedValueIndex := 0
  else
    RolePage.SelectedValueIndex := 1;

  AddressPage := CreateInputQueryPage(
    RolePage.ID,
    'Servidor central',
    'Informe onde está o computador servidor',
    'Digite o nome ou IP do servidor. Ex.: CPEx-SERVER ou 192.168.0.10.'
  );
  AddressPage.Add('Nome ou IP do servidor:', False);

  if RequestedServerAddress() <> '' then
    AddressPage.Values[0] := RequestedServerAddress()
  else if (ExistingUrl <> '') and (Lowercase(ExistingUrl) <> 'http://localhost:8550') then
    AddressPage.Values[0] := ExistingUrl;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = AddressPage.ID) and SelectedServerMode();
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Value: String;
begin
  Result := True;
  if (CurPageID = AddressPage.ID) and not SelectedServerMode() then
  begin
    Value := Trim(AddressPage.Values[0]);
    if Value = '' then
    begin
      MsgBox(
        'Informe o nome ou IP do computador servidor antes de continuar.',
        mbError,
        MB_OK
      );
      Result := False;
      Exit;
    end;
    if Pos(' ', Value) > 0 then
    begin
      MsgBox(
        'O endereço do servidor não pode conter espaços. Use o nome do computador ou o IP.',
        mbError,
        MB_OK
      );
      Result := False;
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  PowerShellPath: String;
  Params: String;
  StopServerComponents: String;
begin
  Result := '';
  NeedsRestart := False;
  WizardForm.StatusLabel.Caption := 'Preparando a instalação e encerrando a versão anterior...';

  if SelectedServerMode() or ExistingServerInstall then
    StopServerComponents :=
      ' $tasks = @(''ClimateTestManager-Server'',''ClimateTestManager-Background'',''ClimateTestManager-Notifications'');' +
      ' foreach ($task in $tasks) {' +
      '   Stop-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue;' +
      '   Disable-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue | Out-Null;' +
      ' };' +
      ' & taskkill.exe /F /T /IM ClimateTestServer.exe 2>$null | Out-Null;' +
      ' & taskkill.exe /F /T /IM ClimateTestNotifier.exe 2>$null | Out-Null;'
  else
    StopServerComponents := '';

  PowerShellPath := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
  Params := '-NoProfile -ExecutionPolicy Bypass -Command "& {' +
    ' $ErrorActionPreference = ''SilentlyContinue'';' +
    StopServerComponents +
    ' & taskkill.exe /F /T /IM ClimateTestManager.exe 2>$null | Out-Null;' +
    ' Start-Sleep -Milliseconds 500;' +
    ' exit 0' +
    '}"';

  if not Exec(PowerShellPath, Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    Result := 'O instalador não conseguiu preparar a atualização. Feche o ClimateTest Manager e tente novamente. Código CTM-UPD-001.';
    Exit;
  end;

  if ResultCode <> 0 then
    Result := 'A versão anterior não pôde ser encerrada automaticamente. Código CTM-UPD-' +
      IntToStr(ResultCode) + '. Feche o ClimateTest Manager e tente novamente.';
end;

function TestClientConnection(ServerUrl: String; var ExitCode: Integer): Boolean;
var
  Params: String;
begin
  Params := '--check-only --url "' + ServerUrl + '"';
  Result := Exec(
    ExpandConstant('{app}\{#MyAppExeName}'),
    Params,
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    ExitCode
  ) and (ExitCode = 0);
end;

procedure WriteModeFiles();
var
  AppServerMarker: String;
  AppClientMarker: String;
  DataServerMarker: String;
  DataClientMarker: String;
begin
  ForceDirectories(ExpandConstant('{commonappdata}\ClimateTestManager'));
  SaveStringToFile(
    ExpandConstant('{commonappdata}\ClimateTestManager\server.url'),
    ConfiguredServerUrl,
    False
  );

  AppServerMarker := ExpandConstant('{app}\server-mode.marker');
  AppClientMarker := ExpandConstant('{app}\client-mode.marker');
  DataServerMarker := ExpandConstant('{commonappdata}\ClimateTestManager\server-mode.marker');
  DataClientMarker := ExpandConstant('{commonappdata}\ClimateTestManager\client-mode.marker');

  if InstallAsServer then
  begin
    DeleteFile(AppClientMarker);
    DeleteFile(DataClientMarker);
    SaveStringToFile(AppServerMarker, 'server', False);
    SaveStringToFile(DataServerMarker, 'server', False);
  end
  else
  begin
    DeleteFile(AppServerMarker);
    DeleteFile(DataServerMarker);
    SaveStringToFile(AppClientMarker, 'client', False);
    SaveStringToFile(DataClientMarker, 'client', False);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Params: String;
  PowerShellPath: String;
begin
  if CurStep <> ssPostInstall then
    Exit;

  InstallAsServer := SelectedServerMode();
  ConfiguredServerUrl := CurrentServerUrl();
  ServerConfigured := False;
  ServerConfigExitCode := -1;
  ClientReachable := False;
  ClientConfigExitCode := -1;
  WriteModeFiles();

  PowerShellPath := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
  if InstallAsServer then
  begin
    WizardForm.StatusLabel.Caption := 'Configurando e verificando o servidor central...';
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
    if ServerConfigured then
      ClientReachable := TestClientConnection(ConfiguredServerUrl, ClientConfigExitCode);
  end
  else
  begin
    WizardForm.StatusLabel.Caption := 'Configurando a estação e verificando o servidor central...';
    if ExistingServerInstall then
      Exec(
        PowerShellPath,
        '-NoProfile -ExecutionPolicy Bypass -File "' +
          ExpandConstant('{app}\uninstall_server_tasks.ps1') + '"',
        '',
        SW_HIDE,
        ewWaitUntilTerminated,
        ResultCode
      );
    ClientReachable := TestClientConnection(ConfiguredServerUrl, ClientConfigExitCode);
  end;
end;

function ShouldLaunchApplication(): Boolean;
begin
  if InstallAsServer then
    Result := ServerConfigured
  else
    Result := True;
end;

function IsServerModeInstall(): Boolean;
begin
  Result :=
    FileExists(ExpandConstant('{app}\server-mode.marker')) or
    FileExists(ExpandConstant('{commonappdata}\ClimateTestManager\server-mode.marker'));
end;

procedure CurPageChanged(CurPageID: Integer);
var
  LogDirectory: String;
begin
  if CurPageID <> wpFinished then
    Exit;

  LogDirectory := ExpandConstant('{commonappdata}\ClimateTestManager\Logs');
  if InstallAsServer then
  begin
    if ServerConfigured and ClientReachable then
    begin
      WizardForm.FinishedHeadingLabel.Caption := 'ClimateTest Manager pronto para uso';
      WizardForm.FinishedLabel.Caption :=
        'O servidor central foi instalado, iniciado e verificado. O aplicativo também respondeu ' +
        'corretamente como cliente Windows.' + #13#10 + #13#10 +
        'Clique em Concluir para abrir o ClimateTest Manager.';
    end
    else
    begin
      WizardForm.FinishedHeadingLabel.Caption := 'A instalação precisa de atenção';
      WizardForm.FinishedLabel.Caption :=
        'Os arquivos foram instalados e os dados existentes foram preservados, mas o servidor ' +
        'central não ficou totalmente operacional.' + #13#10 + #13#10 +
        'Código: CTM-SRV-' + IntToStr(ServerConfigExitCode) + #13#10 +
        'Diagnóstico: ' + LogDirectory + #13#10 + #13#10 +
        'Não apague o banco de dados. O registro acima identifica a etapa que precisa ser corrigida.';
    end;
  end
  else
  begin
    if ClientReachable then
    begin
      WizardForm.FinishedHeadingLabel.Caption := 'ClimateTest Manager pronto para uso';
      WizardForm.FinishedLabel.Caption :=
        'A estação foi instalada e a comunicação com o servidor central foi validada.' + #13#10 + #13#10 +
        'Servidor: ' + ConfiguredServerUrl + #13#10 + #13#10 +
        'Clique em Concluir para abrir o ClimateTest Manager.';
    end
    else
    begin
      WizardForm.FinishedHeadingLabel.Caption := 'Aplicativo instalado - servidor indisponível';
      WizardForm.FinishedLabel.Caption :=
        'O ClimateTest Manager foi instalado corretamente, mas o servidor central não respondeu ' +
        'durante a verificação.' + #13#10 + #13#10 +
        'Servidor configurado: ' + ConfiguredServerUrl + #13#10 +
        'Código: CTM-CLI-001' + #13#10 + #13#10 +
        'Você pode abrir o aplicativo e usar Tentar novamente quando o servidor estiver ligado e ' +
        'conectado à rede.';
    end;
  end;
end;
