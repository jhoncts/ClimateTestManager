param(
    [string]$DataDirectory = ""
)

$ErrorActionPreference = "Stop"
$taskName = "ClimateTestManager-Notifications"
$projectRoot = Split-Path -Parent $PSScriptRoot
$releaseNotifier = Join-Path $projectRoot "dist\ClimateTestManager-v0.8.4\ClimateTestNotifier.exe"
$legacyPackagedNotifier = Join-Path $projectRoot "dist\ClimateTestNotifier.exe"
$developmentPython = Join-Path $projectRoot ".venv\Scripts\pythonw.exe"
$developmentEntry = Join-Path $projectRoot "src\notifier.py"

if ($DataDirectory -and $DataDirectory -match "OneDrive") {
    throw "O banco SQLite ativo nao deve ficar dentro do OneDrive. Use o OneDrive somente para backups."
}

if (Test-Path -LiteralPath $releaseNotifier) {
    $taskCommand = "`"$releaseNotifier`""
}
elseif (Test-Path -LiteralPath $legacyPackagedNotifier) {
    $taskCommand = "`"$legacyPackagedNotifier`""
}
elseif (
    (Test-Path -LiteralPath $developmentPython) -and
    (Test-Path -LiteralPath $developmentEntry)
) {
    $taskCommand = "`"$developmentPython`" `"$developmentEntry`""
}
else {
    throw "Notificador silencioso nao encontrado. Gere os executaveis ou prepare a .venv."
}

if ($DataDirectory) {
    $taskCommand += " --data-directory `"$DataDirectory`""
}

# A acao chama diretamente um executavel sem console (ou pythonw.exe).
# Nenhum powershell.exe/cmd.exe sera aberto nas verificacoes de 5 em 5 minutos.
schtasks.exe /Create /TN $taskName /SC MINUTE /MO 5 /TR $taskCommand /IT /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "O Windows nao conseguiu criar a tarefa agendada."
}

Write-Host "Tarefa '$taskName' instalada. Os prazos serao verificados a cada 5 minutos."
Write-Host "A tarefa funciona com o aplicativo fechado, desde que o Windows esteja ligado e o usuario conectado."
