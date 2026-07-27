# ADR 0005 — Evolução não destrutiva do esquema SQLite

## Contexto

A v0.4.0 acrescenta campos operacionais a bancos que já podem conter ensaios cadastrados na
v0.3.0. `create_all()` cria tabelas ausentes, mas não adiciona colunas a tabelas existentes.

## Decisão

Executar uma migração idempotente antes da inicialização normal. A migração consulta as colunas
existentes e adiciona somente campos operacionais ausentes, todos inicialmente anuláveis. Novas
tabelas continuam sendo criadas pelo metadata do SQLAlchemy.

A versão do esquema é registrada por `PRAGMA user_version`. A v0.4.0 também normaliza o valor
temporário `plan_defined` para `direct_configuration` e cria a tabela pequena
`notifier_run_state`, sem remover registros existentes.

O banco utiliza WAL e tempo de espera de 30 segundos para permitir consultas curtas do aplicativo
e do agente de notificações sem mover o arquivo ativo para uma pasta sincronizada.

## Consequências

- Ensaios existentes são preservados.
- A mesma migração pode ser executada novamente sem duplicar colunas.
- Uma cópia fechada e verificada do banco continua obrigatória antes de cada atualização.
- O OneDrive é destino de backup, nunca local do SQLite ativo.
