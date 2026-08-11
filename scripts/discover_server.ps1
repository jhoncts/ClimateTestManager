param(
    [string]$OutputFile = "",
    [int]$TimeoutMilliseconds = 2200,
    [int]$DiscoveryPort = 8551
)

$ErrorActionPreference = "Stop"
$signature = "CLIMATETEST_DISCOVER_V1"
$results = [System.Collections.Generic.List[object]]::new()
$client = [System.Net.Sockets.UdpClient]::new()
try {
    $client.EnableBroadcast = $true
    $client.Client.ReceiveTimeout = 250
    $payload = [System.Text.Encoding]::UTF8.GetBytes($signature)
    [void]$client.Send($payload, $payload.Length, "255.255.255.255", $DiscoveryPort)

    $deadline = [DateTime]::UtcNow.AddMilliseconds($TimeoutMilliseconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $remote = [System.Net.IPEndPoint]::new([System.Net.IPAddress]::Any, 0)
        try {
            $bytes = $client.Receive([ref]$remote)
        }
        catch [System.Net.Sockets.SocketException] {
            continue
        }
        try {
            $payloadText = [System.Text.Encoding]::UTF8.GetString($bytes)
            $data = $payloadText | ConvertFrom-Json
            if ($data.service -ne "ClimateTestManager") {
                continue
            }
            $ip = $remote.Address.ToString()
            $port = [int]$data.port
            $url = "http://${ip}:$port"
            if (-not ($results | Where-Object { $_.Url -eq $url })) {
                $results.Add([pscustomobject]@{
                    Name = [string]$data.hostname
                    Ip = $ip
                    Port = $port
                    Version = [string]$data.version
                    Url = $url
                })
            }
        }
        catch {
            continue
        }
    }
}
finally {
    $client.Dispose()
}

$lines = @(
    $results |
        Sort-Object Name, Ip |
        ForEach-Object { "{0}|{1}|{2}|{3}|{4}" -f $_.Name, $_.Ip, $_.Port, $_.Version, $_.Url }
)

if ($OutputFile) {
    $parent = Split-Path -Parent $OutputFile
    if ($parent) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $lines | Set-Content -LiteralPath $OutputFile -Encoding UTF8
}
else {
    $lines
}

if ($results.Count -eq 0) { exit 10 }
if ($results.Count -gt 1) { exit 11 }
exit 0
