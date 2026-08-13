# ClimateTest Manager — instalação Windows

Este é o procedimento de implantação do ClimateTest Manager em rede local.

## Um único instalador

Use o mesmo arquivo `ClimateTestManager-Setup-v0.8.4.exe` em todas as máquinas Windows 10/11 de 64 bits.

Durante a instalação escolha apenas o papel do computador:

- **Servidor central**: use somente no computador que permanecerá ligado e guardará o banco de dados.
- **Estação de trabalho**: use nos demais computadores. Informe o nome ou IP do servidor central quando solicitado.

Instale ou atualize sempre o **servidor central primeiro** e, depois que ele estiver funcionando,
instale as estações. Se a descoberta automática encontrar outro servidor central na rede, o
instalador bloqueia uma nova instalação de servidor e orienta a escolher Estação de trabalho.

O ClimateTest Manager abre em uma janela própria do Windows. O navegador não é necessário para o uso normal.

## Servidor central

1. Execute o instalador como administrador.
2. Escolha **Servidor central**.
3. O instalador preserva qualquer banco existente e configura o servidor para iniciar com o Windows.
4. A porta TCP 8550 é liberada somente para a rede local.
5. Ao concluir, abra o ClimateTest Manager pelo atalho criado na Área de Trabalho.
6. No primeiro uso, crie a conta administradora e guarde o código de recuperação em local seguro fora do computador.
7. Em **Configurações**, defina a pasta de backup externo/OneDrive e, se desejado, o SMTP.

Dados de produção:

```text
C:\ProgramData\ClimateTestManager\Data\climatetest_manager.db
```

Logs e diagnósticos:

```text
C:\ProgramData\ClimateTestManager\Logs
```

## Estações de trabalho

1. Execute o mesmo instalador como administrador.
2. Escolha **Estação de trabalho**.
3. Informe o nome ou IP do servidor central, por exemplo `CPEx-SERVER` ou `192.168.0.10`.
4. O instalador grava essa configuração no computador e testa a comunicação.
5. Abra o atalho **ClimateTest Manager**. A aplicação deve abrir em uma janela própria do Windows, sem Chrome/Edge e sem barra de endereço.

A estação não recebe uma cópia do banco de dados. Todas as operações continuam sendo processadas pelo servidor central.

## Manter conectado

Na tela de login existe a opção **Manter conectado neste computador por 30 dias**. A preferência é individual por dispositivo. Ao usar **Sair da conta**, a sessão daquele computador é encerrada.

## Atualizações

Execute o instalador novo por cima da instalação existente. Não desinstale antes e não apague `C:\ProgramData\ClimateTestManager`.

O instalador encerra os processos necessários antes de substituir os executáveis e preserva os dados existentes.

## Diagnósticos

- **CTM-CLI-001**: o aplicativo cliente não conseguiu alcançar o servidor configurado. Confirme se o servidor está ligado, se ambos estão na mesma rede e se o nome/IP informado está correto.
- **CTM-UI-002**: o servidor respondeu, mas a interface não conseguiu ser carregada dentro da janela do aplicativo. Reinicie o aplicativo e consulte os logs se o erro persistir.
- **CTM-SRV-002**: já existe um servidor central detectável na rede. Instale o computador atual como estação de trabalho.
- **CTM-SRV-...**: a instalação do servidor não conseguiu concluir alguma etapa de inicialização. Consulte `C:\ProgramData\ClimateTestManager\Logs` e não apague o banco.
- **CTM-UPD-...**: um processo antigo não pôde ser encerrado durante a atualização. Feche o ClimateTest Manager e execute o instalador novamente.

## Checklist antes de liberar para o laboratório

- [ ] O atalho abre uma janela intitulada **ClimateTest Manager**, e não uma janela vazia chamada Flet.
- [ ] A logo aparece na abertura, no login e no menu.
- [ ] O servidor continua respondendo após reiniciar o Windows.
- [ ] Uma estação instalada com o mesmo instalador conecta pelo nome/IP do servidor.
- [ ] A estação remota apresenta login, e não o cadastro do primeiro administrador.
- [ ] A opção **Manter conectado neste computador por 30 dias** aparece e funciona.
- [ ] Administrador e operador conseguem usar o sistema simultaneamente em computadores diferentes.
- [ ] Ensaios, atividades e notificações criados em uma estação aparecem nas demais.
- [ ] O backup configurado é criado normalmente.
- [ ] Uma atualização por cima da versão existente preserva o banco e volta a iniciar o servidor.
