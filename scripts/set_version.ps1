param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version
)

$ErrorActionPreference = "Stop"

function Replace-InFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Pattern,
        [Parameter(Mandatory = $true)]
        [string]$Replacement
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Arquivo obrigatório não encontrado: $Path"
    }
    $original = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    $updated = [regex]::Replace($original, $Pattern, $Replacement)
    if ($updated -eq $original) {
        throw "O padrão esperado não foi encontrado em $Path. Atualize o script antes de publicar."
    }
    Set-Content -LiteralPath $Path -Value $updated -Encoding UTF8 -NoNewline
}

Replace-InFile `
    -Path "pyproject.toml" `
    -Pattern '(?m)^version\s*=\s*"\d+\.\d+\.\d+"' `
    -Replacement "version = `"$Version`""

Replace-InFile `
    -Path "src\climatetest_manager\__init__.py" `
    -Pattern '(?m)^__version__\s*=\s*"\d+\.\d+\.\d+"' `
    -Replacement "__version__ = `"$Version`""

Replace-InFile `
    -Path "src\client.py" `
    -Pattern '(?m)^VERSION\s*=\s*"\d+\.\d+\.\d+"' `
    -Replacement "VERSION = `"$Version`""

Replace-InFile `
    -Path "installer\ClimateTestManager.iss" `
    -Pattern '(?m)^#define MyAppVersion "\d+\.\d+\.\d+"' `
    -Replacement "#define MyAppVersion `"$Version`""

$installerPath = "installer\ClimateTestManager.iss"
$installer = Get-Content -LiteralPath $installerPath -Raw -Encoding UTF8
$installer = [regex]::Replace(
    $installer,
    'ClimateTestManager-v\d+\.\d+\.\d+',
    "ClimateTestManager-v$Version"
)
Set-Content -LiteralPath $installerPath -Value $installer -Encoding UTF8 -NoNewline

Replace-InFile `
    -Path "scripts\build_windows.ps1" `
    -Pattern '(?m)^\$version\s*=\s*"\d+\.\d+\.\d+"' `
    -Replacement "`$version = `"$Version`""

Replace-InFile `
    -Path "scripts\install_server_tasks.ps1" `
    -Pattern '(?m)^\$version\s*=\s*"\d+\.\d+\.\d+"' `
    -Replacement "`$version = `"$Version`""

$workflowPath = ".github\workflows\release.yml"
$workflow = Get-Content -LiteralPath $workflowPath -Raw -Encoding UTF8
$workflow = [regex]::Replace(
    $workflow,
    'ClimateTestManager-v\d+\.\d+\.\d+',
    "ClimateTestManager-v$Version"
)
$workflow = [regex]::Replace(
    $workflow,
    'ClimateTestManager-Setup-v\d+\.\d+\.\d+',
    "ClimateTestManager-Setup-v$Version"
)
Set-Content -LiteralPath $workflowPath -Value $workflow -Encoding UTF8 -NoNewline

Write-Host "Versão do ClimateTest Manager atualizada para $Version."
Write-Host "Execute os testes antes de criar a tag v$Version."
