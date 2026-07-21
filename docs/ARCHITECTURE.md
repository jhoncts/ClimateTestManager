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
2. O domínio calcula Ts e resolve a condição normativa.
3. O serviço monta o ensaio, a fotografia da regra e o evento de auditoria.
4. O repositório grava o conjunto em uma única transação SQLite.
5. O dashboard consulta os dados persistidos por meio do serviço.

## Próximas evoluções

- Serviços de início, transferência para secagem e encerramento.
- Migrações Alembic versionadas.
- Relógio injetável para testes determinísticos de prazos.
- Notificações locais enquanto a aplicação estiver em execução.
