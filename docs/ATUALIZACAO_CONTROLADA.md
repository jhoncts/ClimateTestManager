# Atualização controlada pelo técnico

O ClimateTest Manager usa um modelo apropriado para portfólio e implantação piloto:

1. uma nova versão é publicada no repositório pessoal do autor;
2. somente o computador configurado como **servidor central** consulta o GitHub;
3. o servidor exibe o aviso ao técnico responsável;
4. o técnico atualiza primeiro o servidor;
5. depois, o técnico distribui o mesmo instalador às estações da rede local;
6. as estações não consultam o GitHub nem instalam versões por iniciativa própria.

Esse mecanismo distribui somente os binários. O banco SQLite permanece exclusivamente no servidor
central e nunca é copiado para uma estação.

## Transição das versões antigas

Versões anteriores a v0.8.7 já consultavam o GitHub em todas as instalações. Esse comportamento não
pode ser alterado retroativamente. Atualize primeiro o servidor para v0.8.7. Para evitar executar o
instalador manualmente em cada estação antiga, copie somente `enable_remote_update_station.ps1` da
pasta de entrega para cada estação e execute uma vez como Administrador, informando o nome do
servidor. Depois disso, o servidor já pode distribuir o instalador v0.8.7 remotamente. A partir da
v0.8.7, somente o servidor central monitorará versões futuras.

## Preparação única de cada estação

Depois de instalar v0.8.7 como **Estação de trabalho**, abra no menu Iniciar:

`ClimateTest Manager - Permitir atualização remota`

Informe o nome do computador servidor central. O script:

- habilita o Windows Remote Management (WinRM);
- limita a regra de firewall aos endereços atuais do servidor informado;
- não grava senha;
- não adiciona curingas a `TrustedHosts`;
- recusa execução no servidor central.

Comando equivalente em PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "C:\Program Files\ClimateTest Manager\enable_remote_update_station.ps1" `
  -CentralComputerName LAB-SERVER
```

Se o IP do servidor mudar, execute novamente esse preparo nas estações. Recomenda-se reservar um IP
para o servidor no roteador ou usar endereçamento fixo administrado.

## Lista de estações

No servidor, edite como Administrador:

`C:\ProgramData\ClimateTestManager\stations.txt`

Use o nome do computador, uma estação por linha:

```text
LAB-ENSAIO-01
LAB-ENSAIO-02
```

Não coloque o próprio servidor na lista. Comentários iniciados por `#` são permitidos.

## Conferência sem instalar

Depois de atualizar o servidor central com o novo instalador, faça primeiro um teste de acesso:

```powershell
$script = "C:\Program Files\ClimateTest Manager\deploy_update_to_stations.ps1"
$setup = "C:\Users\SEU-USUARIO\Downloads\ClimateTestManager-Setup-v0.8.7.exe"

& $script `
  -InstallerPath $setup `
  -PromptForCredential `
  -AllowUnsigned `
  -WhatIf
```

O modo `-WhatIf` abre sessões, confirma a identidade do servidor e verifica se cada destino não é
outro servidor central, mas não copia nem instala arquivos.

## Distribuição real

No menu Iniciar do servidor, abra:

`ClimateTest Manager - Atualizar estações da rede`

Selecione o instalador usado no servidor, confirme conscientemente a versão não assinada e informe
uma conta Administrador válida nas estações. O mesmo processo pode ser executado por comando:

```powershell
& $script `
  -InstallerPath $setup `
  -PromptForCredential `
  -AllowUnsigned `
  -Confirm:$false
```

Para cada estação o script:

1. valida acesso administrativo remoto;
2. confirma que o servidor pertence ao produto `com.jhoncts.climatetestmanager`;
3. recusa máquinas marcadas como servidor central;
4. copia o instalador para `C:\ProgramData\ClimateTestManager\RemoteUpdates`;
5. compara o SHA-256 antes e depois da cópia;
6. instala silenciosamente preservando o papel de estação e o endereço do servidor;
7. executa `--check-only` para confirmar a conexão;
8. grava um relatório CSV em `C:\ProgramData\ClimateTestManager\Logs`.

Uma estação desligada ou inacessível aparece como `FALHOU`; as demais continuam sendo processadas.
Basta ligar a máquina e executar a distribuição novamente.

## Redes sem domínio Windows

Em um grupo de trabalho, o WinRM pode exigir que os nomes exatos das estações estejam em
`TrustedHosts` no servidor. Nunca use `*`. No servidor central, como Administrador:

```powershell
Set-Item WSMan:\localhost\Client\TrustedHosts `
  -Value 'LAB-ENSAIO-01,LAB-ENSAIO-02' `
  -Concatenate `
  -Force
```

Use uma conta administrativa própria para manutenção. O ClimateTest não armazena essa credencial.
Não desabilite o UAC nem altere `LocalAccountTokenFilterPolicy` para contornar permissões.

## Reversão do acesso remoto

Se a administração remota deixar de ser necessária, execute na estação como Administrador:

```powershell
Disable-PSRemoting -Force
Remove-Item `
  -LiteralPath 'C:\ProgramData\ClimateTestManager\remote-update-enabled.json' `
  -Force `
  -ErrorAction SilentlyContinue
```
