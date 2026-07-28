# ADR 0006 — Pausas por recurso e agenda derivada

## Status

Aceita para a v0.4.0.

## Contexto

Uma manutenção pode interromper simultaneamente todos os ensaios que estão na câmara climática ou
na secagem. Alterar apenas o status de cada ensaio perderia a origem comum da parada e dificultaria
o recálculo exato dos prazos.

## Decisão

- Registrar cada indisponibilidade em `resource_pauses`.
- Vincular somente os ensaios afetados no instante em `climate_test_pauses`.
- Manter a situação original da etapa e derivar `Pausado` por vínculo aberto.
- Descontar intervalos de pausa do progresso.
- Deslocar prazos e avisos em uma única transação na retomada.
- Derivar a Agenda dos prazos ativos; não duplicar eventos em uma tabela de calendário.

## Consequências

- Câmara climática e secagem podem ser pausadas de forma independente.
- Ensaios iniciados durante uma parada são bloqueados, evitando vínculos ambíguos.
- Cancelamentos continuam auditáveis mesmo que aconteçam durante uma pausa.
- A agenda sempre reflete o mesmo prazo usado pelo Dashboard e pelo notificador.
