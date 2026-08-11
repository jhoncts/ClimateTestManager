$ErrorActionPreference = "SilentlyContinue"

$taskNames = @(
    "ClimateTestManager-Server",
    "ClimateTestManager-Background",
    "ClimateTestManager-Notifications"
)

foreach ($taskName in $taskNames) {
    Stop-ScheduledTask -TaskName $taskName
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Get-Process -Name "ClimateTestServer" |
    Stop-Process -Force

Remove-ItemProperty `
    -Path "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run" `
    -Name "ClimateTestManagerServer"

& netsh.exe advfirewall firewall delete rule name="ClimateTest Manager - Rede local" | Out-Null
& netsh.exe advfirewall firewall delete rule name="ClimateTest Manager - Descoberta local" | Out-Null

# Os dados em C:\ProgramData\ClimateTestManager são deliberadamente preservados.
# Isso permite reinstalação/atualização sem risco de apagar o banco existente.
