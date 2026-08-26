[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = "Medium")]
param(
    [string]$InstallerPath,
    [string[]]$ComputerName,
    [string]$StationListPath = "$env:ProgramData\ClimateTestManager\stations.txt",
    [string]$ServerAddress,
    [System.Management.Automation.PSCredential]$Credential,
    [switch]$PromptForCredential,
    [switch]$UseSSL,
    [switch]$AllowUnsigned,
    [switch]$Interactive
)

$ErrorActionPreference = "Stop"
$productId = "com.jhoncts.climatetestmanager"
$serviceName = "ClimateTestManager"
$programDataDirectory = Join-Path $env:ProgramData "ClimateTestManager"
$logDirectory = Join-Path $programDataDirectory "Logs"

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Start-ElevatedInteractiveCopy {
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", ('"{0}"' -f $PSCommandPath),
        "-Interactive"
    )
    $process = Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList $arguments `
        -Verb RunAs `
        -Wait `
        -PassThru
    exit $process.ExitCode
}

function Select-InstallerFile {
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Title = "Selecione o instalador do ClimateTest Manager"
    $dialog.Filter = "Instalador ClimateTest|ClimateTestManager-Setup-v*.exe|Executável (*.exe)|*.exe"
    $dialog.Multiselect = $false
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
        throw "Operação cancelada: nenhum instalador foi selecionado."
    }
    return $dialog.FileName
}

function Find-StagedInstaller {
    $approvedDirectory = Join-Path $programDataDirectory "ApprovedUpdates"
    if (-not (Test-Path -LiteralPath $approvedDirectory -PathType Container)) { return "" }
    $centralExecutable = Join-Path $env:ProgramFiles "ClimateTest Manager\ClimateTestManager.exe"
    $centralVersion = ""
    if (Test-Path -LiteralPath $centralExecutable -PathType Leaf) {
        $centralVersion = (Get-Item -LiteralPath $centralExecutable).VersionInfo.ProductVersion.Trim()
    }
    $candidate = Get-ChildItem `
        -LiteralPath $approvedDirectory `
        -Filter "ClimateTestManager-Setup-v*.exe" `
        -File |
        Where-Object {
            (-not $centralVersion) -or ($_.VersionInfo.ProductVersion.Trim() -eq $centralVersion)
        } |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1
    if ($candidate) { return $candidate.FullName }
    return ""
}

function Get-StationNames {
    $names = New-Object System.Collections.Generic.List[string]
    foreach ($value in @($ComputerName)) {
        if ($value -and $value.Trim()) { $names.Add($value.Trim()) }
    }
    if (Test-Path -LiteralPath $StationListPath -PathType Leaf) {
        foreach ($line in Get-Content -LiteralPath $StationListPath -Encoding UTF8) {
            $candidate = ($line -split "#", 2)[0].Trim()
            if ($candidate) { $names.Add($candidate) }
        }
    }
    return @($names | Sort-Object -Unique)
}

function Get-ExpectedChecksum {
    param([Parameter(Mandatory = $true)][string]$Path)

    $checksumPath = $Path -replace '\.exe$', '-SHA256.txt'
    if (-not (Test-Path -LiteralPath $checksumPath -PathType Leaf)) { return "" }
    $content = Get-Content -LiteralPath $checksumPath -Raw -Encoding ASCII
    $match = [regex]::Match($content, '(?i)\b[0-9a-f]{64}\b')
    if (-not $match.Success) {
        throw "O arquivo de SHA-256 existe, mas seu conteúdo é inválido: $checksumPath"
    }
    return $match.Value.ToLowerInvariant()
}

if ($Interactive -and -not (Test-IsAdministrator)) {
    Start-ElevatedInteractiveCopy
}
if (-not (Test-IsAdministrator)) {
    throw "Abra o PowerShell como Administrador para distribuir atualizações."
}
if (-not (Test-Path -LiteralPath (Join-Path $programDataDirectory "server-mode.marker"))) {
    throw "Este comando só pode ser executado no servidor central do ClimateTest Manager."
}
if ($Interactive -and -not $InstallerPath) {
    $InstallerPath = Find-StagedInstaller
    if ($InstallerPath) {
        Write-Host "Instalador aprovado encontrado automaticamente: $InstallerPath"
    } else {
        $InstallerPath = Select-InstallerFile
    }
}
if (-not $InstallerPath) {
    throw "Informe -InstallerPath ou execute o atalho interativo instalado no servidor central."
}
$InstallerPath = (Resolve-Path -LiteralPath $InstallerPath).Path
if ([IO.Path]::GetFileName($InstallerPath) -notmatch '^ClimateTestManager-Setup-v\d+\.\d+\.\d+\.exe$') {
    throw "O arquivo selecionado não tem o nome oficial do instalador ClimateTest Manager."
}

$stations = @(Get-StationNames)
if ($stations.Count -eq 0) {
    throw "Nenhuma estação encontrada. Preencha $StationListPath com um nome de computador por linha."
}
$localNames = @($env:COMPUTERNAME, "localhost", ".", "127.0.0.1")
$stations = @($stations | Where-Object { $localNames -notcontains $_ })
if ($stations.Count -eq 0) {
    throw "A lista contém apenas o servidor central; inclua os nomes das estações."
}

if (-not $ServerAddress) {
    $ServerAddress = "http://$($env:COMPUTERNAME):8550"
}
$ServerAddress = $ServerAddress.Trim().TrimEnd("/")
if ($ServerAddress -notmatch '^https?://[^/\s]+(?::\d+)?$') {
    throw "Endereço do servidor inválido: $ServerAddress"
}
$identity = Invoke-RestMethod -Uri "$ServerAddress/climatetest-server.json" -TimeoutSec 5
if (($identity.product_id -ne $productId) -or
    ($identity.service -ne $serviceName) -or
    ([int]$identity.protocol -ne 1)) {
    throw "O endereço informado não pertence ao servidor ClimateTest Manager."
}
$centralBuild = (Invoke-WebRequest `
    -UseBasicParsing `
    -Uri "$ServerAddress/server-build.txt" `
    -TimeoutSec 5).Content.Trim()

$installerItem = Get-Item -LiteralPath $InstallerPath
$installerVersion = $installerItem.VersionInfo.ProductVersion.Trim()
$centralExecutable = Join-Path $env:ProgramFiles "ClimateTest Manager\ClimateTestManager.exe"
if (Test-Path -LiteralPath $centralExecutable -PathType Leaf) {
    $centralVersion = (Get-Item -LiteralPath $centralExecutable).VersionInfo.ProductVersion.Trim()
    if ($centralVersion -ne $installerVersion) {
        throw (
            "Atualize primeiro o servidor central. Servidor: v$centralVersion; " +
            "instalador selecionado: v$installerVersion."
        )
    }
}

$actualHash = (Get-FileHash -LiteralPath $InstallerPath -Algorithm SHA256).Hash.ToLowerInvariant()
$expectedHash = Get-ExpectedChecksum -Path $InstallerPath
if ($expectedHash -and ($actualHash -ne $expectedHash)) {
    throw "O SHA-256 do instalador não corresponde ao arquivo oficial publicado."
}
if (-not $expectedHash) {
    Write-Warning "Arquivo SHA-256 complementar não encontrado; será usado o hash local $actualHash."
}
$signature = Get-AuthenticodeSignature -LiteralPath $InstallerPath
if ($signature.Status -ne "Valid") {
    if ($Interactive -and -not $AllowUnsigned) {
        $confirmation = Read-Host "Instalador sem assinatura pública. Digite ATUALIZAR para continuar"
        if ($confirmation -ceq "ATUALIZAR") { $AllowUnsigned = $true }
    }
    if (-not $AllowUnsigned) {
        throw "Instalador sem assinatura Authenticode válida. Use -AllowUnsigned somente após conferir o SHA-256."
    }
    Write-Warning "Distribuição autorizada com instalador não assinado; SHA-256 conferido: $actualHash"
}

if ($Interactive -or $PromptForCredential) {
    $Credential = Get-Credential -Message "Informe uma conta Administrador válida nas estações"
}

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$reportPath = Join-Path $logDirectory "remote-update-$timestamp.csv"
$results = New-Object System.Collections.Generic.List[object]

Write-Host "Servidor central: $ServerAddress ($centralBuild)"
Write-Host "Instalador: v$installerVersion"
Write-Host "Estações: $($stations -join ', ')"

foreach ($station in $stations) {
    $session = $null
    $startedAt = Get-Date
    try {
        Write-Host "[$station] Verificando acesso remoto..." -ForegroundColor Cyan
        $sessionParameters = @{
            ComputerName = $station
            ErrorAction = "Stop"
        }
        if ($Credential) { $sessionParameters.Credential = $Credential }
        if ($UseSSL) { $sessionParameters.UseSSL = $true }
        $session = New-PSSession @sessionParameters

        $readiness = Invoke-Command -Session $session -ScriptBlock {
            param($ExpectedProductId, $CentralAddress)
            $programData = Join-Path $env:ProgramData "ClimateTestManager"
            if (Test-Path -LiteralPath (Join-Path $programData "server-mode.marker")) {
                throw "A máquina remota é um servidor central e não será alterada como estação."
            }
            $identity = Invoke-RestMethod `
                -Uri "$CentralAddress/climatetest-server.json" `
                -TimeoutSec 5
            if ($identity.product_id -ne $ExpectedProductId) {
                throw "A estação não alcançou a identidade correta do servidor central."
            }
            $remoteDirectory = Join-Path $programData "RemoteUpdates"
            New-Item -ItemType Directory -Path $remoteDirectory -Force | Out-Null
            return $remoteDirectory
        } -ArgumentList $productId, $ServerAddress

        $remoteInstaller = Join-Path ([string]$readiness) $installerItem.Name
        if ($WhatIfPreference) {
            $results.Add([pscustomobject]@{
                Computer = $station
                Status = "PRONTO"
                Version = $installerVersion
                Detail = "Acesso remoto e servidor central verificados; nenhuma alteração feita."
                StartedAt = $startedAt.ToString("s")
                FinishedAt = (Get-Date).ToString("s")
            })
            continue
        }

        if (-not $PSCmdlet.ShouldProcess($station, "Instalar ClimateTest Manager v$installerVersion")) {
            continue
        }
        Write-Host "[$station] Copiando e verificando o instalador..." -ForegroundColor Cyan
        Copy-Item -LiteralPath $InstallerPath -Destination $remoteInstaller -ToSession $session -Force
        $remoteHash = Invoke-Command -Session $session -ScriptBlock {
            param($Path)
            (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
        } -ArgumentList $remoteInstaller
        if ($remoteHash -ne $actualHash) {
            throw "O SHA-256 mudou durante a cópia para a estação."
        }

        Write-Host "[$station] Instalando silenciosamente..." -ForegroundColor Cyan
        $verification = Invoke-Command -Session $session -ScriptBlock {
            param($Path, $CentralAddress, $ExpectedHash, $ExpectedVersion)
            $programData = Join-Path $env:ProgramData "ClimateTestManager"
            $logDirectory = Join-Path $programData "Logs"
            New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
            $arguments = @(
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART",
                "/SP-",
                "/CLOSEAPPLICATIONS",
                "/FORCECLOSEAPPLICATIONS",
                "/ROLE=client",
                "/SERVERADDRESS=$CentralAddress",
                ('/LOG="{0}"' -f (Join-Path $logDirectory "remote-update-installer.log"))
            )
            $setup = Start-Process `
                -FilePath $Path `
                -ArgumentList $arguments `
                -Wait `
                -PassThru
            if ($setup.ExitCode -ne 0) {
                throw "O instalador retornou o código $($setup.ExitCode)."
            }
            $savedAddress = (Get-Content `
                -LiteralPath (Join-Path $programData "server.url") `
                -Raw).Trim()
            if ($savedAddress -ne $CentralAddress) {
                throw "O endereço do servidor não foi preservado após a instalação."
            }
            if (-not (Test-Path -LiteralPath (Join-Path $programData "client-mode.marker"))) {
                throw "O marcador de estação não foi criado."
            }
            $client = Join-Path $env:ProgramFiles "ClimateTest Manager\ClimateTestManager.exe"
            $installedVersion = (Get-Item -LiteralPath $client).VersionInfo.ProductVersion.Trim()
            if ($installedVersion -ne $ExpectedVersion) {
                throw "Versão instalada inesperada: $installedVersion."
            }
            $check = Start-Process `
                -FilePath $client `
                -ArgumentList @("--check-only", "--url", $CentralAddress) `
                -Wait `
                -PassThru
            if ($check.ExitCode -ne 0) {
                throw "O cliente instalado não alcançou o servidor. Código $($check.ExitCode)."
            }
            if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -ne
                $ExpectedHash) {
                throw "Falha na verificação final do instalador copiado."
            }
            return [pscustomobject]@{
                Version = $installedVersion
                Server = $savedAddress
            }
        } -ArgumentList $remoteInstaller, $ServerAddress, $actualHash, $installerVersion

        $results.Add([pscustomobject]@{
            Computer = $station
            Status = "ATUALIZADO"
            Version = $verification.Version
            Detail = "Servidor: $($verification.Server)"
            StartedAt = $startedAt.ToString("s")
            FinishedAt = (Get-Date).ToString("s")
        })
        Write-Host "[$station] Atualização confirmada." -ForegroundColor Green
    }
    catch {
        $results.Add([pscustomobject]@{
            Computer = $station
            Status = "FALHOU"
            Version = ""
            Detail = $_.Exception.Message
            StartedAt = $startedAt.ToString("s")
            FinishedAt = (Get-Date).ToString("s")
        })
        Write-Warning "[$station] $($_.Exception.Message)"
    }
    finally {
        if ($session) { Remove-PSSession -Session $session -ErrorAction SilentlyContinue }
    }
}

$results | Export-Csv -LiteralPath $reportPath -NoTypeInformation -Encoding UTF8
$results | Format-Table Computer, Status, Version, Detail -AutoSize
Write-Host "Relatório: $reportPath"

$failed = @($results | Where-Object Status -eq "FALHOU")
if ($failed.Count -gt 0) { exit 2 }
exit 0
