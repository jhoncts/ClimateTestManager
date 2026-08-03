# Evidência de verificação automatizada — candidata v0.5.0

Data: 03/08/2026

Ambiente: Linux, Python 3.12.13. O ambiente foi usado para verificar código, regras, banco e
montagem dos controles. A validação específica do executável, DPAPI, notificações e Agendador de
Tarefas continua obrigatoriamente no Windows.

## Resultado

| Verificação | Resultado |
|---|---|
| `python -m ruff check .` | Aprovado, nenhuma ocorrência |
| `python -m ruff format --check .` | Aprovado, 59 arquivos formatados |
| `python -m pytest -q` | **142 testes aprovados** |
| Cobertura de instruções | **80%** (`4.178` instruções; `831` não exercitadas) |
| `git diff --check` | Aprovado para arquivos rastreados |
| Patch sobre a entrega anterior | Aplicação limpa e árvore resultante idêntica ao pacote completo |

## Controles adicionados nesta rodada

- barra lateral recolhível com preservação do conteúdo;
- hierarquia visual das ações em tempo real e de registro posterior;
- verificação de integridade do banco antes da abertura;
- verificação do backup, integridade referencial e manifesto SHA-256;
- recriação de uma cópia diária corrompida sem substituir o banco ativo;
- registro e encerramento controlado de falhas do sistema;
- identificação normativa na interface;
- matriz de conformidade, protocolo, procedimento e avaliação de riscos.

## Limitação da evidência

Este resultado demonstra verificação automatizada, não validação de uso. Anexar ao protocolo a
saída gerada no código/pacote liberado e completar os testes de Windows, migração, SMTP, tarefa em
segundo plano, backup externo e restauração. O aprovador deve registrar o hash do ZIP efetivamente
instalado.
