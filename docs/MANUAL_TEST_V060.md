# Implantação e validação da v0.6.0

## Resultado esperado

A v0.6.0 centraliza o banco SQLite no computador servidor do laboratório. Nenhum operador abre,
sincroniza ou grava diretamente o arquivo `.db`: os navegadores acessam a aplicação pelo endereço
privado do servidor e todas as regras são executadas nele.

## Instalação do servidor

1. No computador que permanece ligado, execute `ClimateTestManager-Server-Setup-v0.6.0.exe`.
2. Autorize a instalação como administrador do Windows.
3. O instalador cria as tarefas `ClimateTestManager-Server` e
   `ClimateTestManager-Background` sob `SYSTEM`, além de
   `ClimateTestManager-Notifications` na sessão interativa. Ele libera somente a porta TCP 8550
   no perfil de rede privado e abre `http://localhost:8550`.
4. Crie o administrador inicial no navegador aberto no próprio servidor.
5. Guarde o código de recuperação exibido uma única vez, fora do computador servidor.
6. Ao atualizar uma base da v0.5, abra o endereço no próprio servidor e guarde o código criado
   automaticamente. Depois, o administrador local pode renová-lo em **Configurações → Conta**.
7. Entre em **Configurações**, defina o backup externo/OneDrive e configure o SMTP.

O banco fica na pasta do perfil Windows que executou o instalador:

```text
%LOCALAPPDATA%\ClimateTestManager\Data\climatetest_manager.db
```

## Acesso dos operadores

No computador ou celular conectado à mesma rede privada, abra:

```text
http://NOME-DO-SERVIDOR:8550
```

Substitua `NOME-DO-SERVIDOR` pelo nome do computador servidor. O administrador cria cada conta em
**Usuários** e entrega somente usuário e senha ao operador. Uma estação remota nunca recebe a tela
de criação do primeiro administrador.

## Recuperação do administrador

Se os dados da conta principal forem cadastrados incorretamente ou o acesso for perdido:

1. Abra `http://localhost:8550` no próprio servidor.
2. Selecione **Recuperar administrador neste servidor**.
3. Informe o código de recuperação e os dados corretos.
4. Todas as sessões da conta são revogadas e um novo código é gerado; o anterior deixa de valer.

Se o administrador ainda consegue entrar, prefira corrigir a conta em **Usuários**.

## Falhas e notificações

- Todos os usuários podem registrar uma falha, escolhendo um motivo, descrevendo o ocorrido e a
  ação tomada.
- A prioridade é definida automaticamente pelo catálogo controlado.
- Falhas aparecem na central interna e por e-mail somente para administradores.
- Prazos operacionais aparecem na central de todos os usuários.
- Somente administradores veem o histórico das falhas e podem registrar ação corretiva e encerrar.

## Proteção e limites

- Acesso por navegador impede que operadores apaguem o banco por engano.
- WAL, `busy_timeout`, transações curtas, verificação de integridade e backups com manifesto
  SHA-256 permanecem ativos.
- O backup externo deve ficar em outro dispositivo ou serviço com histórico de versões. Nenhum
  software consegue garantir proteção absoluta contra malware executado com a mesma conta do
  servidor.
- A v0.6.0 é destinada a uma rede privada confiável. Não encaminhe a porta 8550 no roteador e não
  exponha o endereço diretamente à internet. Acesso externo futuro deve usar HTTPS e VPN.

## Roteiro de aceitação

Marque cada item após verificar:

- [ ] O servidor inicia novamente após reiniciar o Windows, mesmo antes do login de um usuário.
- [ ] E-mails e backups continuam sendo processados antes do login; o toast aparece após o login
  na conta Windows que instalou o sistema.
- [ ] Um segundo computador abre o endereço pelo nome do servidor.
- [ ] A estação remota mostra apenas login.
- [ ] Administrador e operador entram simultaneamente com contas diferentes.
- [ ] Um ensaio criado pelo operador aparece para o administrador.
- [ ] Uma falha registrada pelo operador recebe prioridade automática.
- [ ] A falha aparece apenas na central do administrador.
- [ ] O e-mail da falha chega somente aos administradores ativos.
- [ ] O administrador encerra a falha com uma ação corretiva.
- [ ] Um aviso operacional aparece na central do operador e do administrador.
- [ ] O backup externo é criado e o manifesto informa `quick_check: ok`.
- [ ] A logo aparece no atalho, login, menu, e-mail e notificação do Windows.

Registre computador, Windows, horário, responsável e evidências da execução antes de declarar a
versão liberada para uso oficial.
