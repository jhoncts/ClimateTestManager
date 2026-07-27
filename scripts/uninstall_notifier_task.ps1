$ErrorActionPreference = "Stop"
$taskName = "ClimateTestManager-Notifications"

schtasks.exe /Delete /TN $taskName /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "A tarefa '$taskName' nao foi encontrada ou nao pôde ser removida."
}

Write-Host "Tarefa '$taskName' removida. Os ensaios e o historico foram preservados."
