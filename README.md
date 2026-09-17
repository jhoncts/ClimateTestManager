<div align="center">

# ClimateTest Manager

**Gestão de ensaios de resistência climática com rastreabilidade, automação e operação em rede local.**

[![Quality](https://github.com/jhoncts/ClimateTestManager/actions/workflows/quality.yml/badge.svg)](https://github.com/jhoncts/ClimateTestManager/actions/workflows/quality.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Flet](https://img.shields.io/badge/Flet-0.86.4-0175C2)
![Version](https://img.shields.io/badge/version-0.8.7-238636)
![Platform](https://img.shields.io/badge/platform-Windows-0078D4?logo=windows11&logoColor=white)

</div>

## Visão geral

O **ClimateTest Manager** é um projeto pessoal criado para substituir controles operacionais em planilhas por um sistema local, auditável e acessível na rede privada. O software centraliza ensaios, usuários, prazos, histórico de alterações, notificações, backups e regras de negócio relacionadas à **ABNT NBR IEC 60079-0:2020**.

A solução foi evoluída de uma aplicação desktop para uma arquitetura **cliente-servidor**, mantendo o banco no servidor e permitindo acesso simultâneo por estações da rede sem compartilhar diretamente o arquivo SQLite.

> **Status:** v0.8.7 — portfólio pessoal e implantação piloto controlada.

## O que este projeto demonstra

| Área | Implementação |
| --- | --- |
| Regras de negócio | Cálculo de `Ts`, condições normativas, tolerâncias, estados e validações operacionais |
| Persistência | SQLite, SQLAlchemy e migrações com Alembic |
| Segurança | Login, perfis de acesso, PBKDF2 com salt, recuperação controlada e sessões |
| Rastreabilidade | Histórico de ações, correções auditáveis, registro de falhas e responsáveis |
| Automação | Prazos, agenda, avisos Windows, e-mails e tarefas em segundo plano |
| Confiabilidade | Backups automáticos, verificação SQLite, manifesto SHA-256 e retenção de cópias |
| Distribuição | Empacotamento e instalador Windows para servidor e estações |
| Qualidade | Pytest, Ruff e GitHub Actions em Windows e Linux |

## Principais recursos

### Operação dos ensaios

- cadastro por `Tamb + ΔT`, `Ts`, condição personalizada ou Tabela 17;
- cálculo automático de `Ts = Tamb + ΔT`;
- controle de entrada, retirada nominal, tolerância, secagem e conclusão;
- pausa e retomada com deslocamento automático dos prazos;
- correção auditável de horários e dados operacionais;
- dashboard, filtros, detalhes completos e agenda mensal;
- exportação dos resultados em CSV.

### Usuários e rastreabilidade

- administrador inicial criado somente no servidor;
- perfis de **Administrador** e **Operador**;
- autenticação por usuário ou e-mail;
- sessão persistente opcional;
- nome real do responsável registrado nas ações técnicas;
- trilha de auditoria, motivos controlados e registro de falhas do sistema.

### Notificações e continuidade

- avisos nativos do Windows em segundo plano;
- e-mails automáticos para prazos e alertas administrativos;
- backup local diário com retenção das 30 cópias mais recentes;
- segunda cópia opcional em pasta externa ou OneDrive;
- verificação de integridade e hash SHA-256 de cada cópia automática.

## Arquitetura

```text
Estações da rede
      │
      ▼
Servidor ClimateTest Manager
      │
      ├── aplicação / interface Flet
      ├── serviços e regras de negócio
      ├── SQLAlchemy + Alembic
      ├── SQLite local no servidor
      ├── notificações / e-mail
      └── backups e auditoria
```

Estrutura principal:

```text
ClimateTestManager/
├── docs/                    # arquitetura, regras e validação
├── installer/               # arquivos do instalador Windows
├── scripts/                 # automações de build e manutenção
├── src/
│   ├── main.py
│   ├── server.py
│   └── climatetest_manager/
│       ├── database/
│       ├── domain/
│       ├── repositories/
│       ├── services/
│       └── ui/
└── tests/
```

## Stack

- **Python 3.12**
- **Flet 0.86.4**
- **SQLAlchemy 2.0**
- **SQLite**
- **Alembic**
- **Pytest + pytest-cov**
- **Ruff**
- **PyInstaller / Flet Pack**
- **GitHub Actions**

## Executar em desenvolvimento

No Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
flet run src/main.py
```

Para executar o servidor LAN:

```powershell
python src/server.py --data-directory "C:\ClimateTestManager\Dados"
```

Servidor local:

```text
http://localhost:8550
```

Estações da rede:

```text
http://NOME-DO-SERVIDOR:8550
```

## Qualidade

O pipeline de CI executa o projeto em **Ubuntu** e **Windows** com:

```powershell
ruff check .
ruff format --check .
pytest
```

O fluxo de release também gera e valida os artefatos de distribuição para Windows.

## Gerar o instalador

```powershell
.\scripts\build_windows.ps1
```

O processo gera o instalador, pacote ZIP, hash SHA-256 e manifesto de atualização da versão.

## Documentação técnica

- [Arquitetura](docs/ARCHITECTURE.md)
- [Regras de negócio](docs/BUSINESS_RULES.md)
- [Guia de desenvolvimento](docs/DEVELOPMENT.md)
- [Instalação no Windows](docs/INSTALACAO_WINDOWS.md)
- [Atualização controlada](docs/ATUALIZACAO_CONTROLADA.md)
- [Isolamento entre produtos](docs/PRODUCT_ISOLATION.md)
- [Dossiê de conformidade](docs/compliance/README.md)
- [CHANGELOG](CHANGELOG.md)

## Autoria, independência e dados

Projeto pessoal e independente criado e mantido por **Jhon Cleiton** para portfólio, aprendizado e demonstração técnica. O projeto não pertence, não representa e não é endossado por empregadores, laboratórios ou organizações onde tenham ocorrido testes autorizados.

Dados publicados em demonstrações devem ser fictícios. Consulte também [NOTICE.md](NOTICE.md) e [LICENSE](LICENSE).

---

<div align="center">

**Projeto desenvolvido com foco em software útil, rastreável e aplicável a um problema real.**

</div>
