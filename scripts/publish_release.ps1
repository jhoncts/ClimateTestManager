param(
    [switch]$Push
)

$ErrorActionPreference = "Stop"

function Get-ProjectVersion {
    $line = Select-String -Path "pyproject.toml" -Pattern '^version\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"' |
        Select-Object -First 1
    if (-not $line) {
        throw "Não foi possível localizar a versão em pyproject.toml."
    }
    return $line.Matches[0].Groups[1].Value
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git não foi encontrado."
}
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) não foi encontrado. Instale-o ou publique a tag manualmente."
}

$branch = (git branch --show-current).Trim()
if ($branch -ne "main") {
    throw "Publique atualizações somente a partir da branch main. Branch atual: $branch"
}

$status = git status --porcelain
if ($status) {
    throw "Existem alterações locais. Faça commit ou descarte antes de publicar."
}

& gh auth status | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "O GitHub CLI não está autenticado. Execute: gh auth login"
}

& git fetch origin main --tags
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível atualizar as referências do GitHub."
}

$localHead = (git rev-parse HEAD).Trim()
$remoteHead = (git rev-parse origin/main).Trim()
if ($localHead -ne $remoteHead) {
    throw "A branch main local não corresponde à origin/main. Execute git pull --ff-only origin main."
}

$version = Get-ProjectVersion
$tag = "v$version"
$existing = git tag --list $tag
if ($existing) {
    throw "A tag $tag já existe. Atualize a versão do projeto antes de publicar outra atualização."
}

Write-Host "ClimateTest Manager $tag pronto para publicação."
Write-Host "Ao publicar a tag, o GitHub Actions irá testar, gerar o instalador e criar a Release."
Write-Host "As máquinas instaladas consultarão essa Release automaticamente e validarão o SHA-256."

if (-not $Push) {
    Write-Host ""
    Write-Host "Nenhuma alteração foi enviada. Para publicar de verdade, execute:"
    Write-Host ".\scripts\publish_release.ps1 -Push"
    exit 0
}

& git tag -a $tag -m "ClimateTest Manager $tag"
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível criar a tag $tag."
}

try {
    & git push origin $tag
    if ($LASTEXITCODE -ne 0) {
        throw "O GitHub recusou o envio da tag."
    }
}
catch {
    & git tag -d $tag | Out-Null
    throw
}

Write-Host ""
Write-Host "$tag enviada com sucesso."
Write-Host "Acompanhe a ação 'Build Windows release' no GitHub."
Write-Host "Não envie o EXE manualmente às estações que já possuem o ClimateTest Manager."
