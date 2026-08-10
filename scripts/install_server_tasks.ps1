param(
    [Parameter(Mandatory = $true)]
    [string]$InstallDirectory,
    [Parameter(Mandatory = $true)]
    [string]$DataDirectory,
    [int]$Port = 8550
)

$ErrorActionPreference = "Stop"
$serverTaskName = "ClimateTestManager-Server"
$backgroundTaskName = "ClimateTestManager-Background"
$notifierTaskName = "ClimateTestManager-Notifications"
$serverExecutable = Join-Path $InstallDirectory "ClimateTestServer.exe"
$notifierExecutable = Join-Path $InstallDirectory "ClimateTestNotifier.exe"

if (-not (Test-Path -LiteralPath $serverExecutable)) {
    throw "ClimateTestServer.exe nao foi encontrado no diretorio de instalacao."
}
if (-not (Test-Path -LiteralPath $notifierExecutable)) {
    throw "ClimateTestNotifier.exe nao foi encontrado no diretorio de instalacao."
}

New-Item -ItemType Directory -Path $DataDirectory -Force | Out-Null
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$serverPrincipal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest
$notifierPrincipal = New-ScheduledTaskPrincipal `
    -UserId $identity `
    -LogonType Interactive `
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

$notifierAction = New-ScheduledTaskAction `
    -Execute $notifierExecutable `
    -Argument "--data-directory `"$DataDirectory`" --channels desktop"
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
    -Principal $serverPrincipal `
    -Settings $settings `
    -Description "E-mails e backups do ClimateTest Manager" `
    -Force | Out-Null

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

$firewallName = "ClimateTest Manager - Rede local"
Get-NetFirewallRule -DisplayName $firewallName -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule
New-NetFirewallRule `
    -DisplayName $firewallName `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort $Port `
    -Profile Private | Out-Null

Start-ScheduledTask -TaskName $serverTaskName
Start-ScheduledTask -TaskName $backgroundTaskName

$shortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "ClimateTest Manager.url"
$serverUrl = "http://$env:COMPUTERNAME`:$Port"
Set-Content -LiteralPath $shortcutPath -Encoding ASCII -Value @(
    "[InternetShortcut]"
    "URL=$serverUrl"
    "IconFile=$InstallDirectory\ClimateTestManager.exe"
    "IconIndex=0"
)

Write-Host "Servidor configurado em $serverUrl"
