# Publicação de Releases no GitHub

O repositório pessoal público `jhoncts/ClimateTestManager` funciona como catálogo de versões do
portfólio. Somente o servidor central consulta a Release estável mais recente. As estações recebem
a versão pela distribuição controlada na LAN descrita em
[ATUALIZACAO_CONTROLADA.md](ATUALIZACAO_CONTROLADA.md).

## Publicação gratuita sem certificado

Durante o estágio de portfólio, o workflow permite publicar um instalador sem Authenticode. O
GitHub executa os testes, gera o instalador, publica o SHA-256, cria o manifesto e emite um atestado
de proveniência. A Release e a documentação deixam explícito que o Windows pode mostrar “Editor
desconhecido”.

O SHA-256 detecta alteração do arquivo, mas não substitui a confiança pública de uma assinatura de
código. Quando houver distribuição comercial, o workflow já aceita um certificado sem mudar o
mecanismo de atualização.

## Preparação do GitHub CLI

```powershell
winget install --id GitHub.cli -e
gh auth login
```

Escolha `GitHub.com`, `HTTPS` e autenticação pelo navegador.

## Preparar uma versão futura

Escolha versão e revisão novas:

```powershell
.\scripts\set_version.ps1 -Version 0.8.8 -BuildRevision R13-AAAAMMDD
```

Atualize `CHANGELOG.md`, crie as notas da versão e valide:

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\pytest.exe
.\scripts\build_windows.ps1
```

O build gera:

- `ClimateTestManager-Setup-vX.Y.Z.exe`;
- `ClimateTestManager-Setup-vX.Y.Z-SHA256.txt`;
- `ClimateTestManager-vX.Y.Z-windows.zip`;
- `update-manifest.json`.

## Publicar

Depois de revisar e integrar as alterações na branch principal:

```powershell
git switch main
git pull --ff-only origin main
git tag -a v0.8.7 -m 'ClimateTest Manager v0.8.7'
git push origin v0.8.7
```

O GitHub Actions confere a versão, executa os testes, compila, verifica o instalador e publica a
Release. Para verificar um instalador baixado:

```powershell
gh attestation verify .\ClimateTestManager-Setup-v0.8.7.exe --repo jhoncts/ClimateTestManager
Get-FileHash .\ClimateTestManager-Setup-v0.8.7.exe -Algorithm SHA256
```

Compare o resultado com `ClimateTestManager-Setup-v0.8.7-SHA256.txt` anexado à mesma Release.

## O que acontece depois da publicação

1. O servidor central consulta o manifesto ao abrir e a cada seis horas.
2. O técnico recebe o aviso somente nesse computador.
3. O servidor baixa, confere e instala a versão após confirmação do técnico.
4. O técnico usa o atalho de distribuição para atualizar as estações da rede.
5. Cada estação recebe exatamente o mesmo EXE, confere o hash e testa a conexão ao final.

É necessário permitir HTTPS para `github.com`, `api.github.com`,
`release-assets.githubusercontent.com` e `objects.githubusercontent.com` somente no servidor
central. As estações precisam apenas alcançar o servidor e permitir a administração WinRM
configurada explicitamente pelo responsável.

## Assinatura futura opcional

Quando houver certificado Authenticode `.pfx`, cadastre:

```powershell
$certificado = 'C:\CAMINHO-SEGURO\climatetest-codesigning.pfx'
$certificadoBase64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($certificado))
$certificadoBase64 | gh secret set WINDOWS_SIGNING_CERTIFICATE_BASE64 --repo jhoncts/ClimateTestManager
Remove-Variable certificadoBase64

gh secret set WINDOWS_SIGNING_CERTIFICATE_PASSWORD --repo jhoncts/ClimateTestManager
gh secret set WINDOWS_SIGNING_TIMESTAMP_URL --body 'http://timestamp.digicert.com' --repo jhoncts/ClimateTestManager
```

Certificados e senhas nunca devem ser adicionados ao repositório.
