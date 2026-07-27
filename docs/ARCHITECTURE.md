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

Em produção, o SQLite será criado na pasta de dados do usuário. No Windows, o caminho esperado é
semelhante a:

```text
%LOCALAPPDATA%\ClimateTestManager\climatetest_manager.db
```

Isso evita problemas de permissão em `Program Files` e impede que uma atualização do executável
apague os dados do laboratório.

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

O contrato `NotificationProvider` prepara novos canais. A v0.4.0 implementa somente o toast local;
e-mail e calendário automático exigirão login e autorização OAuth.

### Evolução do SQLite

Antes de `create_all()`, uma migração idempotente acrescenta colunas ausentes aos bancos antigos.
O SQLite usa WAL e `busy_timeout` para coordenar as transações curtas da janela principal e do
notificador. O arquivo ativo permanece local; backups fechados podem ser copiados ao OneDrive.

### Compatibilidade do campo Marcação Ex

A versão 0.3.0 não solicita Marcação Ex porque a condição climática depende do EPL. Para manter
compatibilidade com bancos criados pela v0.2.1, a coluna legada `ex_marking` permanece no SQLite e
recebe uma string vazia nos novos cadastros. A coluna será removida somente após a introdução de
migrações versionadas, evitando exigir que o usuário apague ou recrie o banco existente.

## Próximas evoluções

- Cadastro, login por usuário ou e-mail, sessão persistente opcional, saída da conta, perfis e
  autorização de ações. A persistência guardará uma sessão revogável, nunca a senha em texto puro.
- Tutorial inicial e ajuda contextual resumida para as operações do sistema.
- Migrações Alembic versionadas para mudanças estruturais mais complexas.
- Canais Microsoft 365 de e-mail e calendário por OAuth.
- Política de backup automático com teste periódico de restauração.
