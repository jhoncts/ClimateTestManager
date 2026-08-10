$ErrorActionPreference = "SilentlyContinue"

Stop-ScheduledTask -TaskName "ClimateTestManager-Server"
Unregister-ScheduledTask -TaskName "ClimateTestManager-Server" -Confirm:$false
Unregister-ScheduledTask -TaskName "ClimateTestManager-Background" -Confirm:$false
Unregister-ScheduledTask -TaskName "ClimateTestManager-Notifications" -Confirm:$false
Get-NetFirewallRule -DisplayName "ClimateTest Manager - Rede local" |
    Remove-NetFirewallRule
Remove-Item -LiteralPath (
    Join-Path ([Environment]::GetFolderPath("Desktop")) "ClimateTest Manager.url"
) -Force
