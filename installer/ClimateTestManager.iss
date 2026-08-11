#define MyAppName "ClimateTest Manager"
#define MyAppVersion "0.8.0"
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
WizardStyle=modern dynamic
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
; O arquivo temporário de descoberta fica primeiro para permitir ExtractTemporaryFile com SolidCompression.
Source: "..\dist\ClimateTestManager-v0.8.0\discover_server.ps1"; Flags: dontcopy noencryption
Source: "..\dist\ClimateTestManager-v0.8.0\ClimateTestManager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.8.0\ClimateTestServer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.8.0\ClimateTestNotifier.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.8.0\climatetest.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.8.0\LEIA-ME-PRIMEIRO.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.8.0\install_server_tasks.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.8.0\uninstall_server_tasks.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.8.0\discover_server.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ClimateTestManager-v0.8.0\documentacao-conformidade\*"; DestDir: "{app}\documentacao-conformidade"; Flags: ignoreversion recursesubdirs createallsubdirs

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
  DiscoveryAttempted: Boolean;
  AutoDiscoveredServer: Boolean;
  DiscoveryServerName: String;
  DiscoveryServerIp: String;

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

function DelimitedField(Line: String; FieldNumber: Integer): String;
var
  Working: String;
  Separator: Integer;
  CurrentField: Integer;
begin
  Result := '';
  Working := Line;
  CurrentField := 1;
  while CurrentField < FieldNumber do
  begin
    Separator := Pos('|', Working);
    if Separator = 0 then
      Exit;
    Delete(Working, 1, Separator);
    CurrentField := CurrentField + 1;
  end;
  Separator := Pos('|', Working);
  if Separator > 0 then
    Result := Copy(Working, 1, Separator - 1)
  else
    Result := Working;
  Result := Trim(Result);
end;

function FirstResultLine(Value: String): String;
var
  BreakPosition: Integer;
begin
  Result := Value;
  BreakPosition := Pos(#13, Result);
  if BreakPosition = 0 then
    BreakPosition := Pos(#10, Result);
  if BreakPosition > 0 then
    Result := Copy(Result, 1, BreakPosition - 1);
  Result := Trim(Result);
end;

procedure RunServerDiscovery();
var
  PowerShellPath: String;
  ScriptPath: String;
  OutputPath: String;
  Params: String;
  ResultCode: Integer;
  RawResults: AnsiString;
  FirstLine: String;
  FoundUrl: String;
begin
  if DiscoveryAttempted then
    Exit;
  DiscoveryAttempted := True;
  AutoDiscoveredServer := False;
  DiscoveryServerName := '';
  DiscoveryServerIp := '';

  if RequestedServerAddress() <> '' then
    Exit;

  WizardForm.StatusLabel.Caption := 'Procurando o servidor central na rede local...';
  WizardForm.Refresh();
  ScriptPath := ExpandConstant('{tmp}\discover_server.ps1');
  OutputPath := ExpandConstant('{tmp}\climatetest-discovery.txt');
  DeleteFile(OutputPath);
  PowerShellPath := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
  Params := '-NoProfile -ExecutionPolicy Bypass -File "' + ScriptPath +
    '" -OutputFile "' + OutputPath + '" -TimeoutMilliseconds 2600';

  if not Exec(PowerShellPath, Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    AddressPage.SubCaptionLabel.Caption :=
      'A busca automática não pôde ser iniciada. Informe abaixo o nome ou IP mostrado nas ' +
      'Configurações do computador servidor.';
    Exit;
  end;

  if not LoadStringFromFile(OutputPath, RawResults) then
  begin
    AddressPage.SubCaptionLabel.Caption :=
      'Nenhum servidor central foi encontrado automaticamente. Confirme se ele está ligado e ' +
      'na mesma rede; depois informe abaixo o nome ou IP exibido nas Configurações do servidor.';
    Exit;
  end;

  FirstLine := FirstResultLine(String(RawResults));
  FoundUrl := DelimitedField(FirstLine, 5);
  DiscoveryServerName := DelimitedField(FirstLine, 1);
  DiscoveryServerIp := DelimitedField(FirstLine, 2);
  if FoundUrl = '' then
    Exit;

  AddressPage.Values[0] := FoundUrl;
  if ResultCode = 0 then
  begin
    AutoDiscoveredServer := True;
    AddressPage.SubCaptionLabel.Caption :=
      'Servidor encontrado automaticamente: ' + DiscoveryServerName + ' (' +
      DiscoveryServerIp + '). O instalador usará essa máquina como servidor central.';
  end
  else
  begin
    AddressPage.SubCaptionLabel.Caption :=
      'Mais de um ClimateTest Manager foi encontrado na rede. O primeiro resultado foi ' +
      'preenchido abaixo. Confirme o nome/IP correto antes de continuar.';
  end;
end;

procedure InitializeWizard();
var
  ExistingUrl: String;
  Role: String;
begin
  // O diretório de aplicação ainda não deve ser consultado durante InitializeWizard.
  ExistingServerInstall :=
    FileExists(ExpandConstant('{commonappdata}\ClimateTestManager\Data\climatetest_manager.db')) or
    FileExists(ExpandConstant('{commonappdata}\ClimateTestManager\server-mode.marker'));
  ExistingUrl := ReadExistingServerUrl();
  Role := RequestedRole();
  DiscoveryAttempted := False;
  AutoDiscoveredServer := False;

  ExtractTemporaryFile('discover_server.ps1');

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
    'Localizar o computador servidor',
    'O instalador procura o servidor automaticamente. Esta tela só aparece quando é necessário ' +
    'confirmar ou informar o endereço manualmente.'
  );
  AddressPage.Add('Nome, IP ou endereço do servidor:', False);

  if RequestedServerAddress() <> '' then
    AddressPage.Values[0] := RequestedServerAddress()
  else if (ExistingUrl <> '') and (Lowercase(ExistingUrl) <> 'http://localhost:8550') then
    AddressPage.Values[0] := ExistingUrl;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result :=
    (PageID = AddressPage.ID) and
    (SelectedServerMode() or AutoDiscoveredServer);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Value: String;
begin
  Result := True;

  if (CurPageID = RolePage.ID) and not SelectedServerMode() then
  begin
    if (RequestedServerAddress() = '') and (Trim(AddressPage.Values[0]) = '') then
      RunServerDiscovery();
  end;

  if (CurPageID = AddressPage.ID) and not SelectedServerMode() then
  begin
    Value := Trim(AddressPage.Values[0]);
    if Value = '' then
    begin
      MsgBox(
        'Não foi possível localizar o servidor automaticamente. Informe o nome ou IP do ' +
        'computador servidor. Essa informação aparece em Configurações no servidor central.',
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
  if (not InstallAsServer) and (RequestedServerAddress() = '') and
    (Trim(AddressPage.Values[0]) = '') then
    RunServerDiscovery();
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
        'As estações de trabalho poderão localizar este servidor automaticamente na rede local.' + #13#10 + #13#10 +
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
