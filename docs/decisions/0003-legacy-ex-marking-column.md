# ADR 0003 — Manter temporariamente a coluna legada de Marcação Ex

## Status

Aceita.

## Contexto

A v0.2.1 criou a coluna obrigatória `ex_marking` no SQLite. A validação operacional posterior
confirmou que somente o EPL é necessário para determinar as condições do ensaio climático.
Remover a coluna diretamente impediria novos cadastros nos bancos já criados.

## Decisão

A v0.3.0 remove Marcação Ex da interface e do comando do caso de uso, mas mantém a coluna na
persistência preenchida com string vazia. A remoção física será feita por uma migração versionada
quando o fluxo de migrações estiver incorporado à inicialização da aplicação.

## Consequências

- Bancos da v0.2.1 continuam utilizáveis sem perda de dados.
- Novos cadastros não exigem uma informação sem função nessa etapa do ensaio.
- Existe uma coluna legada documentada até a implantação das migrações.
