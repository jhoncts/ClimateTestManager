param(
    [string]$DataDirectory = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

if ($DataDirectory) {
    $env:CLIMATETEST_DATA_DIR = $DataDirectory
}

$releaseNotifier = Join-Path $projectRoot "dist\ClimateTestManager-v0.6.0\ClimateTestNotifier.exe"
$legacyPackagedNotifier = Join-Path $projectRoot "dist\ClimateTestNotifier.exe"
$developmentPython = Join-Path $projectRoot ".venv\Scripts\pythonw.exe"
$developmentEntry = Join-Path $projectRoot "src\notifier.py"

if (Test-Path -LiteralPath $releaseNotifier) {
    & $releaseNotifier
    exit $LASTEXITCODE
}

if (Test-Path -LiteralPath $legacyPackagedNotifier) {
    & $legacyPackagedNotifier
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $developmentPython)) {
    throw "Notificador nao encontrado. Gere os executaveis ou prepare a .venv."
}

& $developmentPython $developmentEntry
exit $LASTEXITCODE
