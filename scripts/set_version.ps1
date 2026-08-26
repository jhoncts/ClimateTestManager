param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$')]
    [string]$BuildRevision,
    [switch]$SkipWorkflow
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
    if (-not [regex]::IsMatch($original, $Pattern)) {
        throw "O padrão esperado não foi encontrado em $Path. Atualize o script antes de publicar."
    }
    $updated = [regex]::Replace($original, $Pattern, $Replacement)
    if ($updated -ne $original) {
        Set-Content -LiteralPath $Path -Value $updated -Encoding UTF8 -NoNewline
    }
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
    -Path "src\climatetest_manager\__init__.py" `
    -Pattern '(?m)^__build_revision__\s*=\s*"[^"]+"' `
    -Replacement "__build_revision__ = `"$BuildRevision`""

Replace-InFile `
    -Path "src\client.py" `
    -Pattern '(?m)^VERSION\s*=\s*"\d+\.\d+\.\d+"' `
    -Replacement "VERSION = `"$Version`""

Replace-InFile `
    -Path "src\client_r6.py" `
    -Pattern '(?m)^APP_VERSION\s*=\s*"\d+\.\d+\.\d+"' `
    -Replacement "APP_VERSION = `"$Version`""

Replace-InFile `
    -Path "src\client_r6.py" `
    -Pattern '(?m)^BUILD_REVISION\s*=\s*"[^"]+"' `
    -Replacement "BUILD_REVISION = `"$BuildRevision`""

Replace-InFile `
    -Path "src\climatetest_manager\round7_runtime.py" `
    -Pattern '(?m)^BUILD_REVISION\s*=\s*"[^"]+"' `
    -Replacement "BUILD_REVISION = `"$BuildRevision`""

Set-Content -LiteralPath "src\assets\server-build.txt" -Value $BuildRevision -Encoding ascii -NoNewline

Replace-InFile `
    -Path "installer\ClimateTestManager.iss" `
    -Pattern '(?m)^#define MyAppVersion "\d+\.\d+\.\d+"' `
    -Replacement "#define MyAppVersion `"$Version`""

Replace-InFile `
    -Path "installer\ClimateTestManager.iss" `
    -Pattern '(?m)^#define MyBuildRevision "[^"]+"' `
    -Replacement "#define MyBuildRevision `"$BuildRevision`""

$installerPath = "installer\ClimateTestManager.iss"
$installer = Get-Content -LiteralPath $installerPath -Raw -Encoding UTF8
$installer = [regex]::Replace(
    $installer,
    'ClimateTestManager-v\d+\.\d+\.\d+',
    "ClimateTestManager-v$Version"
)
Set-Content -LiteralPath $installerPath -Value $installer -Encoding UTF8 -NoNewline

Replace-InFile `
    -Path "scripts\install_server_tasks.ps1" `
    -Pattern '(?m)^\$version\s*=\s*"\d+\.\d+\.\d+"' `
    -Replacement "`$version = `"$Version`""

Replace-InFile `
    -Path "scripts\install_server_tasks.ps1" `
    -Pattern '(?m)^\$buildRevision\s*=\s*"[^"]+"' `
    -Replacement "`$buildRevision = `"$BuildRevision`""

if (-not $SkipWorkflow) {
    $workflowPath = ".github\workflows\release.yml"
    if (-not (Test-Path -LiteralPath $workflowPath)) {
        throw "Arquivo obrigatório não encontrado: $workflowPath"
    }
    $workflow = Get-Content -LiteralPath $workflowPath -Raw -Encoding UTF8
    if ($workflow -notmatch 'ClimateTestManager-(?:Setup-)?v\d+\.\d+\.\d+') {
        throw "A versão esperada não foi encontrada em $workflowPath."
    }
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
}

Write-Host "Versão do ClimateTest Manager atualizada para $Version."
Write-Host "Revisão de build atualizada para $BuildRevision."
Write-Host "Execute os testes antes de criar a tag v$Version."
