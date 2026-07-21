# ClimateTest Manager

Aplicação desktop para controle de ensaios de resistência climática realizados conforme a
**ABNT NBR IEC 60079-0:2020**.

O projeto nasce para substituir uma planilha operacional por um software local, auditável e
preparado para gerar um executável do Windows sem abrir navegador ou terminal.

> Status: fundação técnica concluída. A interface inicial e o motor normativo da Tabela 17 já
> possuem uma primeira implementação testável. Cadastro, fluxo completo e histórico serão
> desenvolvidos nas próximas etapas.

## Funcionalidades planejadas

- Cadastro e acompanhamento de ensaios climáticos.
- Cálculo de `Ts = Tamb + ΔT`.
- Seleção automática das condições da Tabela 17.
- Escolha entre as opções A e B quando ambas forem permitidas.
- Controle das etapas de câmara e secagem.
- Situação operacional e condição de prazo separadas.
- Dashboard de ensaios ativos e ações necessárias.
- Histórico auditável de alterações.

## Tecnologias

- Python 3.12
- Flet 0.86.1
- SQLite
- SQLAlchemy 2.0
- Alembic
- Pytest
- Ruff
- PyInstaller por meio de `flet pack`

Todas as ferramentas utilizadas são gratuitas ou open source.

## Estrutura

```text
ClimateTestManager/
├── docs/                    # Requisitos, arquitetura e decisões técnicas
├── scripts/                 # Automação de tarefas locais
├── src/
│   ├── assets/              # Ícones e recursos visuais
│   ├── main.py              # Ponto de entrada esperado pelo Flet
│   └── climatetest_manager/
│       ├── database/        # SQLite e modelos SQLAlchemy
│       ├── domain/          # Regras de negócio sem dependência da interface
│       ├── repositories/    # Acesso aos dados
│       ├── services/        # Casos de uso da aplicação
│       └── ui/              # Telas e componentes Flet
└── tests/                   # Testes automatizados
```

## Preparação no Windows 11

Abra a pasta do projeto no VS Code e, no terminal PowerShell, execute:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Se o PowerShell impedir a ativação do ambiente virtual, libere-a apenas para o terminal atual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Executar a aplicação

Com o ambiente virtual ativado:

```powershell
flet run src/main.py
```

O Flet abrirá a aplicação em uma janela nativa do Windows.

## Verificar a qualidade

```powershell
ruff check .
ruff format --check .
pytest
```

## Gerar o executável

O empacotamento deve ser executado no próprio Windows:

```powershell
.\scripts\build_windows.ps1
```

O resultado será criado em `dist/ClimateTestManager.exe`. O comando usa `flet pack`, a
integração oficial do Flet com o PyInstaller, sem habilitar o console de depuração.

## Documentação

- [Regras de negócio](docs/BUSINESS_RULES.md)
- [Arquitetura](docs/ARCHITECTURE.md)
- [Guia de desenvolvimento](docs/DEVELOPMENT.md)
- [Histórico de versões](CHANGELOG.md)

## Aviso normativo

O sistema auxilia a aplicação das regras configuradas, mas não substitui a leitura da norma,
os procedimentos internos do laboratório ou a avaliação técnica responsável. Toda alteração
normativa deverá gerar uma nova versão explícita das regras e seus respectivos testes.
