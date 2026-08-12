$ErrorActionPreference = "Stop"
$version = "0.8.0"
$releaseDir = "dist\ClimateTestManager-v$version"
$releaseZip = "dist\ClimateTestManager-v$version-windows.zip"
$installerPath = "dist\ClimateTestManager-Setup-v$version.exe"
$installerHashPath = "dist\ClimateTestManager-Setup-v$version-SHA256.txt"
$assetsStage = ".release-assets"

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    throw "Ambiente virtual nao encontrado. Crie a .venv e instale o projeto antes de empacotar."
}

if (Test-Path -LiteralPath $releaseDir) {
    Remove-Item -LiteralPath $releaseDir -Recurse -Force
}
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

if (Test-Path -LiteralPath $assetsStage) {
    Remove-Item -LiteralPath $assetsStage -Recurse -Force
}
New-Item -ItemType Directory -Path $assetsStage -Force | Out-Null
Copy-Item "src\assets\*" $assetsStage -Recurse -Force
New-Item -ItemType Directory -Path (Join-Path $assetsStage "icons") -Force | Out-Null
Copy-Item `
    "src\assets\brand\climatetest-logo.png" `
    (Join-Path $assetsStage "favicon.png") `
    -Force
Copy-Item `
    "src\assets\brand\climatetest-logo.png" `
    (Join-Path $assetsStage "icons\loading-animation.png") `
    -Force

# O Flet baixa o runtime desktop na primeira execução. Em runners do GitHub essa
# transferência pode ser encerrada remotamente de forma transitória. Uma falha de
# rede não deve invalidar um release cujo código e testes já passaram, portanto o
# empacotamento é tentado novamente com espera curta e crescente.
$packSucceeded = $false
$packAttempts = 3
for ($attempt = 1; $attempt -le $packAttempts; $attempt++) {
    Write-Host "Empacotando ClimateTestManager.exe (tentativa $attempt de $packAttempts)..."
    .\.venv\Scripts\flet.exe pack src/client_r5.py `
        --name ClimateTestManager `
        --icon "src\assets\brand\climatetest.ico" `
        --add-data "$assetsStage;assets" `
        --product-name "ClimateTest Manager" `
        --product-version $version `
        --file-version "$version.0" `
        --file-description "Cliente desktop do ClimateTest Manager - R5" `
        --company-name "ClimateTest Manager" `
        --copyright "Copyright (c) 2026 Jhon Cleiton" `
        --distpath $releaseDir `
        --yes

    if ($LASTEXITCODE -eq 0) {
        $packSucceeded = $true
        break
    }

    if ($attempt -lt $packAttempts) {
        $waitSeconds = 8 * $attempt
        Write-Warning "Empacotamento Flet falhou. Nova tentativa em $waitSeconds segundos."
        Start-Sleep -Seconds $waitSeconds
    }
}
if (-not $packSucceeded) {
    throw "Falha ao empacotar ClimateTestManager.exe apos $packAttempts tentativas."
}

.\.venv\Scripts\python.exe -m PyInstaller src/server.py `
    --name ClimateTestServer `
    --noconsole `
    --onefile `
    --icon "src\assets\brand\climatetest.ico" `
    --add-data "$assetsStage;assets" `
    --collect-all flet_web `
    --distpath $releaseDir `
    --clean `
    --noconfirm
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao empacotar ClimateTestServer.exe."
}

.\.venv\Scripts\python.exe -m PyInstaller src/notifier.py `
    --name ClimateTestNotifier `
    --noconsole `
    --onefile `
    --icon "src\assets\brand\climatetest.ico" `
    --add-data "$assetsStage;assets" `
    --distpath $releaseDir `
    --clean `
    --noconfirm
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao empacotar ClimateTestNotifier.exe."
}

Copy-Item "docs\INSTALACAO_WINDOWS.md" (Join-Path $releaseDir "LEIA-ME-PRIMEIRO.md")
Copy-Item "src\assets\brand\climatetest.ico" (Join-Path $releaseDir "climatetest.ico")
Copy-Item "scripts\install_server_tasks.ps1" $releaseDir
Copy-Item "scripts\uninstall_server_tasks.ps1" $releaseDir
Copy-Item "scripts\discover_server.ps1" $releaseDir
$complianceDir = Join-Path $releaseDir "documentacao-conformidade"
New-Item -ItemType Directory -Path $complianceDir -Force | Out-Null
Copy-Item "docs\compliance\*" $complianceDir -Recurse -Force

if (Test-Path -LiteralPath $releaseZip) {
    Remove-Item -LiteralPath $releaseZip -Force
}
Compress-Archive -Path "$releaseDir\*" -DestinationPath $releaseZip

$innoCommand = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
$programFilesX86 = [Environment]::GetFolderPath("ProgramFilesX86")
$innoCandidates = @(
    $innoCommand.Source,
    (Join-Path $programFilesX86 "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
) | Where-Object { $_ }
$iscc = $innoCandidates |
    Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1
if (-not $iscc) {
    throw "Inno Setup 6 nao encontrado. O instalador da v$version e obrigatorio."
}

& $iscc "installer\ClimateTestManager.iss"
if ($LASTEXITCODE -ne 0) {
    throw "O Inno Setup nao conseguiu gerar o instalador."
}
if (-not (Test-Path -LiteralPath $installerPath)) {
    throw "O build terminou sem gerar $installerPath."
}
if (-not (Test-Path -LiteralPath $releaseZip)) {
    throw "O build terminou sem gerar $releaseZip."
}

$installerHash = (Get-FileHash -LiteralPath $installerPath -Algorithm SHA256).Hash.ToLowerInvariant()
"SHA256  $installerHash  $(Split-Path -Leaf $installerPath)" |
    Set-Content -LiteralPath $installerHashPath -Encoding ascii

Remove-Item -LiteralPath $assetsStage -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Instalador criado em $installerPath"
Write-Host "SHA-256 criado em $installerHashPath"
Write-Host "Pacote criado em $releaseZip"
Write-Host "Executaveis prontos em $releaseDir"
