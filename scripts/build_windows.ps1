$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    throw "Ambiente virtual nao encontrado. Crie a .venv e instale o projeto antes de empacotar."
}

flet pack src/main.py `
    --name ClimateTestManager `
    --product-name "ClimateTest Manager" `
    --product-version "0.1.0" `
    --file-version "0.1.0.0" `
    --file-description "Gerenciador de ensaios de resistencia climatica" `
    --company-name "ClimateTest Manager" `
    --copyright "Copyright (c) 2026 Jhon Cleiton" `
    --distpath dist `
    --yes

Write-Host "Executavel criado em dist\ClimateTestManager.exe"
