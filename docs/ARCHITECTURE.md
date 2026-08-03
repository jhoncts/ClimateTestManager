# Arquitetura

## Objetivo

A arquitetura separa as regras normativas da interface e do banco. Com isso, uma regra pode ser
testada sem abrir o Flet e sem criar um arquivo SQLite.

## Camadas

```text
UI (Flet)
    ↓
Services (casos de uso)
    ↓
Domain (regras e entidades)
    ↓
Repositories (contratos de persistência)
    ↓
Database (SQLAlchemy + SQLite)
```

As dependências devem apontar para dentro: a camada de domínio não conhece Flet, SQLAlchemy ou
detalhes do sistema operacional.

## Decisões iniciais

### Estrutura `src`

O código importável fica dentro de `src/climatetest_manager`. Isso reduz o risco de os testes
funcionarem apenas porque foram executados na pasta errada e aproxima o ambiente de testes do
pacote realmente instalado.

### Entrada fina para o Flet

`src/main.py` contém somente a chamada de inicialização. A aplicação real fica no pacote
`climatetest_manager`, permitindo testes e futuras formas de execução.

### Banco fora da pasta do programa

Antes da primeira inicialização do SQLite, o responsável confirma uma pasta local. O caminho
padrão sugerido no Windows é semelhante a:

```text
%LOCALAPPDATA%\ClimateTestManager\climatetest_manager.db
```

Isso evita problemas de permissão em `Program Files` e impede que uma atualização do executável
apague os dados do laboratório. A decisão fica em `storage.json`, na pasta de configuração do
usuário, para que o aplicativo e o notificador encontrem o mesmo banco. A variável
`CLIMATETEST_DATA_DIR` continua tendo prioridade somente para desenvolvimento e validações
isoladas.

O assistente rejeita OneDrive, Dropbox, Google Drive, iCloud e caminhos de rede como local do
banco aberto. Se um banco da versão anterior existir no local padrão e o responsável escolher
outra pasta local vazia, a API de backup do SQLite cria uma cópia consistente sem apagar a
origem.

### Fotografia da regra normativa

Os dados resultantes da Tabela 17 devem ser gravados no ensaio. O histórico continuará mostrando
qual condição foi aplicada mesmo se uma versão futura do motor normativo for atualizada.

A tabela `climate_condition_snapshots` armazena essa fotografia em uma relação de um para um com
`climate_tests`. Ela registra temperaturas, umidade, durações, tolerâncias, opção e identificador
da regra. A criação da nova tabela é compatível com bancos vazios da versão 0.1.0.

### Fluxo do cadastro

1. A tela coleta e valida os dados do operador.
2. O serviço registra a origem escolhida: cálculo por Tamb + ΔT, Ts informado ou Personalizado.
3. Quando houver Ts exato, o domínio resolve a condição normativa; no modo Personalizado, o
   sistema preserva a configuração efetivamente informada sem criar valores fictícios.
4. O serviço monta o ensaio, a fotografia da regra e o evento de auditoria.
5. O repositório grava o conjunto em uma única transação SQLite.
6. O dashboard consulta os dados persistidos por meio do serviço.

### Fluxo operacional

1. O serviço valida a transição a partir da situação atual.
2. O horário real inicia a etapa e gera os prazos nominal e máximo.
3. A operação, os horários e o evento de auditoria são gravados na mesma transação.
4. Os avisos da etapa são persistidos com chaves únicas.
5. O dashboard calcula a condição de prazo no instante da consulta.

O relógio é injetável nos serviços para que fronteiras como saída nominal e limite máximo sejam
testadas de forma determinística.

### Pausas por equipamento

`resource_pauses` registra cada indisponibilidade da câmara climática ou da secagem.
`climate_test_pauses` fotografa quais ensaios estavam no recurso naquele instante. A pausa e todos
os vínculos são criados em uma transação; a retomada encerra os intervalos, desloca prazos e
reagenda avisos na mesma transação.

A situação principal continua indicando a etapa (`Na Câmara` ou `Em Secagem`). O estado `Pausado`
é derivado do vínculo aberto, evitando perder qual equipamento e qual etapa devem ser retomados.
O progresso desconta a interseção de todos os intervalos de pausa com a etapa.

O notificador exclui ensaios com pausa aberta da consulta de avisos vencidos. Assim, um prazo
antigo não dispara durante manutenção; na retomada, as datas persistidas são atualizadas.

### Dashboard, agenda e tema

O dashboard consome uma projeção do serviço que já exclui finalizados e cancelados e inclui
progresso, pausa e próximo prazo. A Agenda usa os mesmos prazos ativos para montar uma visão mensal,
sem manter um segundo calendário ou duplicar dados.

As cores ficam centralizadas em `AppColors`. A preferência claro/escuro é salva em
`preferences.json`, na mesma pasta de dados, e aplicada antes de reconstruir os controles Flet.

### Agente de notificações

`src/notifier.py` é um ponto de entrada independente. A tarefa agendada do Windows chama
diretamente `ClimateTestNotifier.exe` ou `pythonw.exe` a cada 5 minutos, sem iniciar PowerShell ou
CMD. Ele abre o banco, entrega somente avisos vencidos e ainda não enviados, registra o resultado
em `notifier_run_state` e termina. Portanto, não existe um segundo processo mantendo o banco aberto
o tempo todo.

O contrato `NotificationProvider` atende separadamente o toast local e o SMTP. As colunas
`desktop_sent_at` e `email_sent_at` tornam os canais idempotentes: uma falha no SMTP não repete um
toast já entregue. Os destinatários são os e-mails das contas ativas.

A configuração SMTP é restrita ao administrador. Os campos não sensíveis ficam em
`preferences.json`; a senha é protegida pela DPAPI do Windows e vinculada à conta que realizou a
configuração. A senha protegida é prioritária; `CLIMATETEST_SMTP_PASSWORD` serve somente como
alternativa de teste quando ainda não existe credencial salva. Senhas de app do Gmail são
normalizadas sem os espaços usados apenas para apresentação. A interface oferece modelos de
provedor e reutiliza o mesmo tutorial no diálogo de configuração e no Guia de uso; o envio
continua centralizado no agente local. O envelope informa explicitamente remetente e
destinatários, analisa recusas devolvidas por `send_message` e adiciona `Date` e `Message-ID`. O
teste inclui o remetente como cópia diagnóstica e mostra um comprovante de aceitação; os eventos
automáticos permanecem restritos aos e-mails das contas ativas.

As correções de horários convergem para `change_operational_timestamp`. O caso de uso recebe um
dos quatro identificadores controlados, valida a ordem entre as etapas, recalcula somente o prazo
dependente de uma entrada e grava os valores anterior e novo na auditoria. A interface não envia
um rótulo ambíguo como “entrada da câmara”.

No pacote do Windows, o aplicativo resolve `ClimateTestNotifier.exe` ao lado do executável
principal e cria a tarefa diretamente com `schtasks.exe`. Em desenvolvimento, aceita o notificador
gerado em `dist` ou `pythonw.exe`. A ativação não depende de PowerShell nem da árvore do código.

### Evolução do SQLite

Antes de `create_all()`, uma migração idempotente acrescenta colunas ausentes aos bancos antigos.
O SQLite usa WAL e `busy_timeout` para coordenar as transações curtas da janela principal e do
notificador. O arquivo ativo permanece local; somente backups fechados podem ser copiados ao
OneDrive.

Na abertura, a API nativa de backup do SQLite cria no máximo uma cópia por dia em `backups`. Para
um banco existente, a tentativa acontece antes da migração; para um banco novo, após a criação.
Somente as 30 cópias automáticas mais recentes são mantidas. Quando existe uma pasta externa
configurada, a mesma API cria ali uma segunda cópia diária consistente, também com retenção de 30
arquivos. O notificador executa essa verificação diária mesmo quando a janela principal está
fechada. Depois de gravar a cópia, o serviço abre o arquivo em modo somente leitura, executa
`PRAGMA quick_check` e `PRAGMA foreign_key_check`, calcula SHA-256 e grava um manifesto JSON ao
lado do `.db`. Uma cópia diária inválida é recriada a partir do banco ativo. O banco ativo também
passa por `quick_check` antes de qualquer migração e não é aberto quando a verificação falha. O
backup manual continua permitindo que o usuário escolha outro destino.

### Falhas do sistema

`system_incidents` preserva categoria, impacto, descrição, ação imediata, autor e data do relato.
Qualquer usuário autenticado pode registrar uma falha. Somente um Administrador pode encerrá-la,
acrescentando ação corretiva, responsável e data sem substituir a descrição original. O registro
apoia a avaliação prevista em 7.10, 7.11.3(e) e 8.7 da ABNT NBR ISO/IEC 17025:2017; a decisão sobre
resultados afetados continua pertencendo ao procedimento de trabalho não conforme do laboratório.

### Autenticação e autorização local

`AuthenticationService` concentra validação de identidade, senha, sessão e perfis. A UI nunca
consulta diretamente o hash da senha. `UserRepository` persiste:

- `users`: identidade, perfil, status, conclusão do primeiro acesso e foto opcional;
- `user_sessions`: somente SHA-256 do token opaco, validade e revogação;
- `security_audit_events`: eventos de login e administração de contas.

As senhas usam PBKDF2-HMAC-SHA256, salt aleatório por conta e 600 mil iterações. O primeiro
usuário é administrador. A sessão comum dura até 12 horas; **Manter conectado** usa 30 dias.
Alteração de senha, redefinição ou desativação revoga as sessões anteriores.

`ClimateTestService` recebe um `actor_provider`. Assim, o nome do usuário é resolvido no instante
de cada transação e gravado junto da ação técnica, sem introduzir dependência da autenticação nas
regras normativas.

### Compatibilidade do campo Marcação Ex

A versão 0.3.0 não solicita Marcação Ex porque a condição climática depende do EPL. Para manter
compatibilidade com bancos criados pela v0.2.1, a coluna legada `ex_marking` permanece no SQLite e
recebe uma string vazia nos novos cadastros. A coluna será removida somente após a introdução de
migrações versionadas, evitando exigir que o usuário apague ou recrie o banco existente.

## Próximas evoluções

- Migrações Alembic versionadas para mudanças estruturais mais complexas.
- Assistente de restauração com teste periódico das cópias.
- Transferência auditável da condição de administrador principal. Na v0.5.0 todos os
  administradores ativos têm as mesmas permissões e o sistema apenas protege a existência de ao
  menos um administrador.
