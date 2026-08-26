[CmdletBinding()]
param(
    [string]$CentralComputerName
)

$ErrorActionPreference = "Stop"
$productId = "com.jhoncts.climatetestmanager"
$programDataDirectory = Join-Path $env:ProgramData "ClimateTestManager"

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdministrator)) {
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", ('"{0}"' -f $PSCommandPath),
        "-CentralComputerName", ('"{0}"' -f $CentralComputerName)
    )
    $process = Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList $arguments `
        -Verb RunAs `
        -Wait `
        -PassThru
    exit $process.ExitCode
}

if (-not $CentralComputerName) {
    $CentralComputerName = Read-Host "Digite o nome do computador servidor central"
}
if (-not $CentralComputerName.Trim()) {
    throw "O nome do servidor central é obrigatório."
}
$CentralComputerName = $CentralComputerName.Trim()

if (Test-Path -LiteralPath (Join-Path $programDataDirectory "server-mode.marker")) {
    throw "Este computador é o servidor central. O bootstrap remoto é exclusivo das estações."
}
if (-not (Test-Path -LiteralPath (Join-Path $programDataDirectory "client-mode.marker"))) {
    throw "O ClimateTest Manager não está configurado como estação neste computador."
}

$addresses = @(
    [Net.Dns]::GetHostAddresses($CentralComputerName) |
        Where-Object AddressFamily -eq ([Net.Sockets.AddressFamily]::InterNetwork) |
        ForEach-Object IPAddressToString
)
if ($addresses.Count -eq 0) {
    throw "Não foi possível localizar o servidor central $CentralComputerName."
}

Enable-PSRemoting -Force -SkipNetworkProfileCheck
Set-Service -Name WinRM -StartupType Automatic
Start-Service -Name WinRM

$firewallRules = @(Get-NetFirewallRule -Name "WINRM-HTTP-In-TCP*" -ErrorAction SilentlyContinue)
if ($firewallRules.Count -eq 0) {
    throw "As regras do Windows Remote Management não foram encontradas."
}
$firewallRules | Set-NetFirewallRule -Enabled True -RemoteAddress $addresses

New-Item -ItemType Directory -Path $programDataDirectory -Force | Out-Null
$marker = [ordered]@{
    product_id = $productId
    central_computer = $CentralComputerName
    allowed_addresses = $addresses
    configured_at = (Get-Date).ToUniversalTime().ToString("o")
}
$marker | ConvertTo-Json | Set-Content `
    -LiteralPath (Join-Path $programDataDirectory "remote-update-enabled.json") `
    -Encoding UTF8

Write-Host "Estação preparada para atualização remota do ClimateTest Manager." -ForegroundColor Green
Write-Host "Servidor autorizado: $CentralComputerName ($($addresses -join ', '))"
Write-Host "Nenhum TrustedHosts nem credencial foram gravados neste computador."
