$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    throw "Ambiente virtual nao encontrado. Crie a .venv e instale o projeto antes de empacotar."
}

flet pack src/main.py `
    --name ClimateTestManager `
    --product-name "ClimateTest Manager" `
    --product-version "0.4.0" `
    --file-version "0.4.0.0" `
    --file-description "Gerenciador de ensaios de resistencia climatica" `
    --company-name "ClimateTest Manager" `
    --copyright "Copyright (c) 2026 Jhon Cleiton" `
    --distpath dist `
    --yes

.\.venv\Scripts\python.exe -m PyInstaller src/notifier.py `
    --name ClimateTestNotifier `
    --noconsole `
    --onefile `
    --distpath dist `
    --clean `
    --noconfirm

Write-Host "Executaveis criados em dist\ClimateTestManager.exe e dist\ClimateTestNotifier.exe"
