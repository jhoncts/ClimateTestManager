# ADR 0002 — Versionar e fotografar regras normativas

- Status: aceito
- Data: 2026-07-21

## Contexto

Ensaios antigos precisam manter a condição que foi efetivamente utilizada, mesmo depois de uma
mudança de norma ou de interpretação interna.

## Decisão

Cada condição calculada recebe um identificador e a edição normativa `IEC60079-0:2020-T17-v1`.
No cadastro, temperaturas, durações, tolerâncias, opção e versão serão persistidas no próprio
ensaio.

## Consequências

- Resultados antigos permanecem auditáveis.
- Alterações de regra exigem uma nova versão e novos testes.
- Não dependeremos de recalcular dados históricos com a regra mais recente.
