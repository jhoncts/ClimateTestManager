param(
    [Parameter(Mandatory = $true)]
    [string]$InstallDirectory,
    [Parameter(Mandatory = $true)]
    [string]$DataDirectory,
    [int]$Port = 8550
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$version = "0.7.0"
$serverTaskName = "ClimateTestManager-Server"
$backgroundTaskName = "ClimateTestManager-Background"
$notifierTaskName = "ClimateTestManager-Notifications"
$firewallName = "ClimateTest Manager - Rede local"
$serverExecutable = Join-Path $InstallDirectory "ClimateTestServer.exe"
$notifierExecutable = Join-Path $InstallDirectory "ClimateTestNotifier.exe"
$productRoot = Split-Path -Parent $DataDirectory
$logDirectory = Join-Path $productRoot "Logs"
$backupRoot = Join-Path $productRoot "Backups"
$statusFile = Join-Path $productRoot "install-status.json"
$legacyDataDirectory = Join-Path $env:LOCALAPPDATA "ClimateTestManager\Data"
$warnings = [System.Collections.Generic.List[string]]::new()
$startupMode = "scheduled-task"

try {
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
}
catch {
    $logDirectory = Join-Path $env:TEMP "ClimateTestManager"
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
}

$logFile = Join-Path $logDirectory ("installer-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

function Write-InstallLog {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [ValidateSet("INFO", "WARN", "ERROR")]
        [string]$Level = "INFO"
    )

    $line = "{0} [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    Add-Content -LiteralPath $logFile -Encoding UTF8 -Value $line
}

function Add-InstallWarning {
    param([Parameter(Mandatory = $true)][string]$Message)

    $warnings.Add($Message)
    Write-InstallLog -Level "WARN" -Message $Message
}

function Remove-ExistingTask {
    param([Parameter(Mandatory = $true)][string]$TaskName)

    try {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($task) {
            Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
            Write-InstallLog "Tarefa antiga removida: $TaskName"
        }
    }
    catch {
        Add-InstallWarning "Não foi possível remover a tarefa antiga '$TaskName': $($_.Exception.Message)"
    }
}

function Test-ServerReady {
    param([int]$Attempts = 30)

    $url = "http://127.0.0.1:$Port/"
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

function Start-DetachedServer {
    """Inicia o servidor por Win32_Process para não prender o instalador ao processo permanente."""

    $commandLine = (
        '"{0}" --host 0.0.0.0 --port {1} --data-directory "{2}"' -f `
            $serverExecutable,
            $Port,
            $DataDirectory
    )
    try {
        $created = Invoke-CimMethod `
            -ClassName Win32_Process `
            -MethodName Create `
            -Arguments @{ CommandLine = $commandLine } `
            -ErrorAction Stop
        if ($null -eq $created -or [int]$created.ReturnValue -ne 0) {
            $code = if ($null -eq $created) { -1 } else { [int]$created.ReturnValue }
            throw "Win32_Process.Create retornou código $code."
        }
        Write-InstallLog "Inicialização direta desacoplada criada. PID=$($created.ProcessId)."
    }
    catch {
        Add-InstallWarning (
            "Não foi possível desacoplar a inicialização direta; usando o método compatível: " +
            $_.Exception.Message
        )
        Start-Process `
            -FilePath $serverExecutable `
            -ArgumentList @(
                "--host", "0.0.0.0",
                "--port", "$Port",
                "--data-directory", "`"$DataDirectory`""
            ) `
            -WindowStyle Hidden
    }
}

function Register-ServerStartup {
    param(
        [Parameter(Mandatory = $true)]
        [System.Management.Automation.ActionPreference]$FailurePreference
    )

    try {
        $serverPrincipal = New-ScheduledTaskPrincipal `
            -UserId "SYSTEM" `
            -LogonType ServiceAccount `
            -RunLevel Highest
        $settings = New-ScheduledTaskSettingsSet `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -ExecutionTimeLimit ([TimeSpan]::Zero) `
            -RestartCount 99 `
            -RestartInterval (New-TimeSpan -Minutes 1) `
            -MultipleInstances IgnoreNew
        $serverAction = New-ScheduledTaskAction `
            -Execute $serverExecutable `
            -Argument "--host 0.0.0.0 --port $Port --data-directory `"$DataDirectory`""
        $serverTrigger = New-ScheduledTaskTrigger -AtStartup
        Register-ScheduledTask `
            -TaskName $serverTaskName `
            -Action $serverAction `
            -Trigger $serverTrigger `
            -Principal $serverPrincipal `
            -Settings $settings `
            -Description "Servidor LAN do ClimateTest Manager" `
            -Force | Out-Null
        Write-InstallLog "Inicialização automática do servidor configurada pelo Agendador de Tarefas."
        return $true
    }
    catch {
        if ($FailurePreference -eq [System.Management.Automation.ActionPreference]::Stop) {
            throw
        }
        Add-InstallWarning "O Agendador de Tarefas não aceitou o servidor: $($_.Exception.Message)"
        return $false
    }
}

function Register-BackgroundTasks {
    param([Parameter(Mandatory = $true)][string]$Identity)

    try {
        $settings = New-ScheduledTaskSettingsSet `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -ExecutionTimeLimit ([TimeSpan]::Zero) `
            -RestartCount 99 `
            -RestartInterval (New-TimeSpan -Minutes 1) `
            -MultipleInstances IgnoreNew
        $systemPrincipal = New-ScheduledTaskPrincipal `
            -UserId "SYSTEM" `
            -LogonType ServiceAccount `
            -RunLevel Highest
        $backgroundAction = New-ScheduledTaskAction `
            -Execute $notifierExecutable `
            -Argument "--data-directory `"$DataDirectory`" --channels email"
        $backgroundTrigger = New-ScheduledTaskTrigger `
            -Once `
            -At (Get-Date).AddMinutes(1) `
            -RepetitionInterval (New-TimeSpan -Minutes 5) `
            -RepetitionDuration (New-TimeSpan -Days 3650)
        Register-ScheduledTask `
            -TaskName $backgroundTaskName `
            -Action $backgroundAction `
            -Trigger $backgroundTrigger `
            -Principal $systemPrincipal `
            -Settings $settings `
            -Description "E-mails e backups do ClimateTest Manager" `
            -Force | Out-Null

        $notifierPrincipal = New-ScheduledTaskPrincipal `
            -UserId $Identity `
            -LogonType Interactive `
            -RunLevel Highest
        $notifierAction = New-ScheduledTaskAction `
            -Execute $notifierExecutable `
            -Argument "--data-directory `"$DataDirectory`" --channels desktop"
        $notifierTrigger = New-ScheduledTaskTrigger `
            -Once `
            -At (Get-Date).AddMinutes(1) `
            -RepetitionInterval (New-TimeSpan -Minutes 5) `
            -RepetitionDuration (New-TimeSpan -Days 3650)
        Register-ScheduledTask `
            -TaskName $notifierTaskName `
            -Action $notifierAction `
            -Trigger $notifierTrigger `
            -Principal $notifierPrincipal `
            -Settings $settings `
            -Description "Avisos operacionais do ClimateTest Manager" `
            -Force | Out-Null
        Write-InstallLog "Tarefas de e-mail, backup e notificações configuradas."
    }
    catch {
        Add-InstallWarning "O servidor foi instalado, mas uma tarefa de aviso não pôde ser configurada: $($_.Exception.Message)"
    }
}

try {
    Write-InstallLog "Iniciando configuração do ClimateTest Manager v$version."
    Write-InstallLog "Diretório de instalação: $InstallDirectory"
    Write-InstallLog "Diretório de dados: $DataDirectory"

    if (-not (Test-Path -LiteralPath $serverExecutable)) {
        throw "ClimateTestServer.exe não foi encontrado no diretório de instalação."
    }
    if (-not (Test-Path -LiteralPath $notifierExecutable)) {
        throw "ClimateTestNotifier.exe não foi encontrado no diretório de instalação."
    }

    foreach ($taskName in @($serverTaskName, $backgroundTaskName, $notifierTaskName)) {
        Remove-ExistingTask -TaskName $taskName
    }
    Get-Process -Name "ClimateTestServer" -ErrorAction SilentlyContinue |
        Stop-Process -Force -ErrorAction SilentlyContinue

    New-Item -ItemType Directory -Path $DataDirectory -Force | Out-Null
    New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

    $targetHasData = Get-ChildItem -LiteralPath $DataDirectory -Force -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ((Test-Path -LiteralPath $legacyDataDirectory) -and (-not $targetHasData)) {
        Write-InstallLog "Dados de uma instalação anterior encontrados em $legacyDataDirectory."
        Copy-Item -Path (Join-Path $legacyDataDirectory "*") -Destination $DataDirectory -Recurse -Force
        Write-InstallLog "Dados anteriores copiados para a pasta central sem apagar a origem."
    }
    elseif ((Test-Path -LiteralPath $legacyDataDirectory) -and $targetHasData) {
        $legacyBackup = Join-Path $backupRoot ("legacy-{0}" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
        New-Item -ItemType Directory -Path $legacyBackup -Force | Out-Null
        Copy-Item -Path (Join-Path $legacyDataDirectory "*") -Destination $legacyBackup -Recurse -Force
        Write-InstallLog "A pasta central já possuía dados. A instalação antiga foi preservada em $legacyBackup."
    }

    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    try {
        & icacls.exe $productRoot `
            /grant:r "*S-1-5-18:(OI)(CI)F" `
            "*S-1-5-32-544:(OI)(CI)F" `
            "${identity}:(OI)(CI)M" `
            /T /C | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Add-InstallWarning "O Windows não aplicou todas as permissões reforçadas. As permissões existentes foram mantidas."
        }
        else {
            Write-InstallLog "Permissões da pasta de dados verificadas."
        }
    }
    catch {
        Add-InstallWarning "Não foi possível reforçar as permissões da pasta de dados; nenhum arquivo foi apagado: $($_.Exception.Message)"
    }

    $serverTaskRegistered = Register-ServerStartup -FailurePreference Continue
    if (-not $serverTaskRegistered) {
        $startupMode = "windows-run-fallback"
        $runKey = "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run"
        $runValue = "`"$serverExecutable`" --host 0.0.0.0 --port $Port --data-directory `"$DataDirectory`""
        New-Item -Path $runKey -Force | Out-Null
        New-ItemProperty `
            -Path $runKey `
            -Name "ClimateTestManagerServer" `
            -Value $runValue `
            -PropertyType String `
            -Force | Out-Null
        Add-InstallWarning "Foi ativado o modo de inicialização compatível do Windows. O servidor iniciará no logon."
    }
    else {
        Remove-ItemProperty `
            -Path "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run" `
            -Name "ClimateTestManagerServer" `
            -ErrorAction SilentlyContinue
    }

    Register-BackgroundTasks -Identity $identity

    try {
        & netsh.exe advfirewall firewall delete rule name="$firewallName" | Out-Null
        & netsh.exe advfirewall firewall add rule `
            name="$firewallName" `
            dir=in `
            action=allow `
            protocol=TCP `
            localport=$Port `
            profile=any `
            remoteip=localsubnet | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Add-InstallWarning "A regra de firewall não pôde ser criada automaticamente. O acesso local continuará funcionando."
        }
        else {
            Write-InstallLog "Firewall liberado somente para a sub-rede local na porta $Port."
        }
    }
    catch {
        Add-InstallWarning "O firewall não pôde ser ajustado automaticamente: $($_.Exception.Message)"
    }

    if ($serverTaskRegistered) {
        try {
            Start-ScheduledTask -TaskName $serverTaskName -ErrorAction Stop
            Write-InstallLog "Tarefa do servidor iniciada."
        }
        catch {
            Add-InstallWarning "A tarefa foi criada, mas não iniciou de imediato: $($_.Exception.Message)"
        }
    }

    if (-not (Test-ServerReady -Attempts 30)) {
        Write-InstallLog -Level "WARN" -Message "Servidor ainda não respondeu pela tarefa. Tentando inicialização direta desacoplada."
        Start-DetachedServer
    }

    if (-not (Test-ServerReady -Attempts 30)) {
        throw "O servidor não respondeu em http://127.0.0.1:$Port após duas tentativas de inicialização."
    }

    try {
        Start-ScheduledTask -TaskName $backgroundTaskName -ErrorAction SilentlyContinue
    }
    catch {
        Add-InstallWarning "A tarefa de segundo plano será executada no próximo ciclo."
    }

    $status = [ordered]@{
        version = $version
        installed_at = (Get-Date).ToString("o")
        server_url = "http://$env:COMPUTERNAME`:$Port"
        local_url = "http://localhost:$Port"
        data_directory = $DataDirectory
        startup_mode = $startupMode
        warnings = @($warnings)
        installer_log = $logFile
    }
    $status | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statusFile -Encoding UTF8

    Write-InstallLog "Servidor verificado com sucesso em http://127.0.0.1:$Port."
    Write-InstallLog "Configuração concluída."
    exit 0
}
catch {
    Write-InstallLog -Level "ERROR" -Message $_.Exception.Message
    Write-InstallLog -Level "ERROR" -Message "A instalação preservou os dados existentes. Consulte este arquivo para diagnóstico: $logFile"
    exit 20
}
