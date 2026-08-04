$ErrorActionPreference = "Stop"
$releaseDir = "dist\ClimateTestManager-v0.5.0"
$releaseZip = "dist\ClimateTestManager-v0.5.0-windows.zip"

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    throw "Ambiente virtual nao encontrado. Crie a .venv e instale o projeto antes de empacotar."
}

if (Test-Path -LiteralPath $releaseDir) {
    Remove-Item -LiteralPath $releaseDir -Recurse -Force
}
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

flet pack src/main.py `
    --name ClimateTestManager `
    --product-name "ClimateTest Manager" `
    --product-version "0.5.0" `
    --file-version "0.5.0.0" `
    --file-description "Gerenciador de ensaios de resistencia climatica" `
    --company-name "ClimateTest Manager" `
    --copyright "Copyright (c) 2026 Jhon Cleiton" `
    --distpath $releaseDir `
    --yes

.\.venv\Scripts\python.exe -m PyInstaller src/notifier.py `
    --name ClimateTestNotifier `
    --noconsole `
    --onefile `
    --distpath $releaseDir `
    --clean `
    --noconfirm

Copy-Item "docs\MANUAL_TEST_V050.md" (Join-Path $releaseDir "LEIA-ME-PRIMEIRO.md")
$complianceDir = Join-Path $releaseDir "documentacao-conformidade"
New-Item -ItemType Directory -Path $complianceDir -Force | Out-Null
Copy-Item "docs\compliance\*" $complianceDir -Recurse -Force

if (Test-Path -LiteralPath $releaseZip) {
    Remove-Item -LiteralPath $releaseZip -Force
}
Compress-Archive -Path "$releaseDir\*" -DestinationPath $releaseZip

Write-Host "Pacote criado em $releaseZip"
Write-Host "Executaveis prontos em $releaseDir"
