$ErrorActionPreference = "Stop"
$version = "0.8.5"
$releaseDir = "dist\ClimateTestManager-v$version"
$releaseZip = "dist\ClimateTestManager-v$version-windows.zip"
$installerPath = "dist\ClimateTestManager-Setup-v$version.exe"
$installerHashPath = "dist\ClimateTestManager-Setup-v$version-SHA256.txt"
$assetsStage = ".release-assets"
$generatedInstaller = "installer\ClimateTestManager.generated.iss"

$packageMetadata = Get-Content -LiteralPath "src\climatetest_manager\__init__.py" -Raw -Encoding UTF8
$buildMatch = [regex]::Match($packageMetadata, '(?m)^__build_revision__\s*=\s*"([^"]+)"')
if (-not $buildMatch.Success) { throw "Revisão de build não encontrada em __init__.py." }
$buildRevision = $buildMatch.Groups[1].Value
$serverBuildRevision = (Get-Content -LiteralPath "src\assets\server-build.txt" -Raw -Encoding ASCII).Trim()
if ($serverBuildRevision -ne $buildRevision) {
    throw "Revisões inconsistentes: pacote=$buildRevision; servidor=$serverBuildRevision."
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) { throw "Ambiente virtual nao encontrado." }
if (Test-Path -LiteralPath $releaseDir) { Remove-Item -LiteralPath $releaseDir -Recurse -Force }
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
if (Test-Path -LiteralPath $assetsStage) { Remove-Item -LiteralPath $assetsStage -Recurse -Force }
New-Item -ItemType Directory -Path $assetsStage -Force | Out-Null
Copy-Item "src\assets\*" $assetsStage -Recurse -Force
New-Item -ItemType Directory -Path (Join-Path $assetsStage "icons") -Force | Out-Null
Copy-Item "src\assets\brand\climatetest-logo.png" (Join-Path $assetsStage "favicon.png") -Force
Copy-Item "src\assets\brand\climatetest-logo.png" (Join-Path $assetsStage "icons\loading-animation.png") -Force

$packSucceeded = $false
for ($attempt = 1; $attempt -le 3; $attempt++) {
    .\.venv\Scripts\flet.exe pack src/client_r6.py --name ClimateTestManager --icon "src\assets\brand\climatetest.ico" --add-data "$assetsStage;assets" --product-name "ClimateTest Manager" --product-version $version --file-version "$version.0" --file-description "Cliente desktop do ClimateTest Manager - v$version / $buildRevision" --company-name "ClimateTest Manager" --copyright "Copyright (c) 2026 Jhon Cleiton" --distpath $releaseDir --yes
    if ($LASTEXITCODE -eq 0) { $packSucceeded = $true; break }
    if ($attempt -lt 3) { Start-Sleep -Seconds (8 * $attempt) }
}
if (-not $packSucceeded) { throw "Falha ao empacotar ClimateTestManager.exe apos 3 tentativas." }

.\.venv\Scripts\python.exe -m PyInstaller src/server.py --name ClimateTestServer --noconsole --onefile --icon "src\assets\brand\climatetest.ico" --add-data "$assetsStage;assets" --collect-all flet_web --distpath $releaseDir --clean --noconfirm
if ($LASTEXITCODE -ne 0) { throw "Falha ao empacotar ClimateTestServer.exe." }
.\.venv\Scripts\python.exe -m PyInstaller src/notifier.py --name ClimateTestNotifier --noconsole --onefile --icon "src\assets\brand\climatetest.ico" --add-data "$assetsStage;assets" --distpath $releaseDir --clean --noconfirm
if ($LASTEXITCODE -ne 0) { throw "Falha ao empacotar ClimateTestNotifier.exe." }

Copy-Item "docs\INSTALACAO_WINDOWS.md" (Join-Path $releaseDir "LEIA-ME-PRIMEIRO.md")
Copy-Item "src\assets\brand\climatetest.ico" (Join-Path $releaseDir "climatetest.ico")
Copy-Item "scripts\uninstall_server_tasks.ps1" $releaseDir
Copy-Item "scripts\discover_server.ps1" $releaseDir
$installScript = Get-Content -LiteralPath "scripts\install_server_tasks.ps1" -Raw -Encoding UTF8
$installScript = [regex]::Replace($installScript, '(?m)^\$version\s*=\s*"[^"]+"', "`$version = `"$version`"")
$installScript = [regex]::Replace($installScript, '(?m)^\$buildRevision\s*=\s*"[^"]+"', "`$buildRevision = `"$buildRevision`"")
Set-Content -LiteralPath (Join-Path $releaseDir "install_server_tasks.ps1") -Value $installScript -Encoding UTF8 -NoNewline
$complianceDir = Join-Path $releaseDir "documentacao-conformidade"
New-Item -ItemType Directory -Path $complianceDir -Force | Out-Null
Copy-Item "docs\compliance\*" $complianceDir -Recurse -Force

if (Test-Path -LiteralPath $releaseZip) { Remove-Item -LiteralPath $releaseZip -Force }
Compress-Archive -Path "$releaseDir\*" -DestinationPath $releaseZip

$innoCommand = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
$programFilesX86 = [Environment]::GetFolderPath("ProgramFilesX86")
$innoCandidates = @($innoCommand.Source, (Join-Path $programFilesX86 "Inno Setup 6\ISCC.exe"), (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")) | Where-Object { $_ }
$iscc = $innoCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 nao encontrado." }
$installerSource = Get-Content -LiteralPath "installer\ClimateTestManager.iss" -Raw -Encoding UTF8
$installerSource = [regex]::Replace($installerSource, '(?m)^#define MyAppVersion "[^"]+"', "#define MyAppVersion `"$version`"")
$installerSource = [regex]::Replace($installerSource, '(?m)^#define MyBuildRevision "[^"]+"', "#define MyBuildRevision `"$buildRevision`"")
Set-Content -LiteralPath $generatedInstaller -Value $installerSource -Encoding UTF8 -NoNewline
& $iscc $generatedInstaller
if ($LASTEXITCODE -ne 0) { throw "O Inno Setup nao conseguiu gerar o instalador." }
if (-not (Test-Path -LiteralPath $installerPath)) { throw "O build terminou sem gerar $installerPath." }

$installerHash = (Get-FileHash -LiteralPath $installerPath -Algorithm SHA256).Hash.ToLowerInvariant()
"SHA256  $installerHash  $(Split-Path -Leaf $installerPath)" | Set-Content -LiteralPath $installerHashPath -Encoding ascii
Remove-Item -LiteralPath $assetsStage -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $generatedInstaller -Force -ErrorAction SilentlyContinue
Write-Host "Instalador criado em $installerPath"
Write-Host "Revisão de build: $buildRevision"
Write-Host "SHA-256 criado em $installerHashPath"
Write-Host "Pacote criado em $releaseZip"
