# ClimateTest Manager

Aplicação desktop para controle de ensaios de resistência climática realizados conforme a
**ABNT NBR IEC 60079-0:2020**.

O projeto nasce para substituir uma planilha operacional por um software local, auditável e
preparado para gerar um executável do Windows sem abrir navegador ou terminal.

> Status: versão 0.4.0 em desenvolvimento. Cadastro, cálculo da Tabela 17, controle de câmara e
> secagem, prazos, histórico e notificações locais já estão funcionais. Ainda não deve ser usada
> como sistema oficial do laboratório.

## Funcionalidades disponíveis

- Cadastro de ensaios climáticos com validação dos campos obrigatórios.
- Cadastro por três formas: Tamb + ΔT, Ts informado ou condição personalizada.
- Quantidade de amostras acompanhada em todas as etapas.
- Cálculo de `Ts = Tamb + ΔT`.
- Consulta automática das condições da Tabela 17.
- Escolha entre as opções A e B quando ambas forem permitidas.
- Normalização das entradas decimais para vírgula e bloqueio de caracteres não numéricos.
- Apresentação das permanências em horas, dias nominais e limite com tolerância.
- Gravação local do ensaio, da condição normativa e do primeiro evento de auditoria.
- Dashboard restrito aos ensaios pendentes, pausados e em andamento, com progresso compacto.
- Início da câmara no horário atual ou em data/hora informada manualmente.
- Cálculo separado da saída nominal e do limite máximo com tolerância de `+30 h`.
- Condição `Em tolerância` entre a saída nominal e o limite máximo; atraso somente após o limite.
- Início da secagem pelo horário real de retirada da câmara e recálculo dos respectivos prazos.
- Pausa global e independente da câmara climática e da secagem, com congelamento da contagem,
  motivo obrigatório e deslocamento automático dos prazos na retomada.
- Correção auditável da entrada registrada da câmara.
- Finalização e cancelamento com motivo obrigatório.
- Correção auditável dos dados e exclusão somente de cadastros não iniciados.
- Lista pesquisável com filtro de situação e tela completa de detalhes.
- Caminho visual do ensaio e registro global de atividades.
- Agenda mensal interna para retirada nominal e limite máximo dos ensaios ativos.
- Exportação dos resultados filtrados em CSV com escolha de local e arquivo de agenda `.ics`.
- Avisos nativos do Windows executados silenciosamente a cada 5 minutos, mesmo com a janela
  principal fechada.
- Tela de Configurações com teste de notificação, última verificação, pasta dos dados e cópia de
  segurança do banco.
- Temas claro e escuro com preferência preservada no computador.
- Migração automática e não destrutiva de bancos criados pela v0.3.0.

## Próximas funcionalidades

- Cadastro com e-mail, nome de usuário único, nome, sobrenome, senha e confirmação de senha.
- Login pelo nome de usuário ou e-mail, opção **Manter conectado**, sessão persistente após
  reiniciar o computador e ação **Sair da conta**. Senhas não serão armazenadas em texto puro.
- Tutorial inicial curto e uma área de ajuda com instruções resumidas para cada função.
- Identificação real do responsável por cada ação.
- Preferências individuais de idioma, formatos e antecedência dos avisos.
- Integração autorizada com Microsoft 365 para calendário e e-mail.
- Política formal de backup, restauração e retenção para uso operacional.

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

## Independência e dados de demonstração

Este é um projeto pessoal e independente desenvolvido para aprendizado e portfólio. Ele não
representa um produto oficial ou endossado por qualquer laboratório. Todos os nomes, processos e
demais dados usados em demonstrações públicas devem ser fictícios.

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
integração oficial do Flet com o PyInstaller, sem habilitar o console de depuração. O mesmo
script também cria `dist/ClimateTestNotifier.exe`, responsável pelos avisos em segundo plano.

## Avisos em segundo plano

Na tela **Configurações**, selecione **Ativar avisos**. O sistema cria uma tarefa do Windows que
verifica os prazos a cada 5 minutos. A janela principal pode permanecer fechada, mas o computador
deve estar ligado e a sessão do Windows iniciada. A tarefa chama diretamente o notificador sem
abrir uma janela de CMD ou PowerShell.

O banco SQLite ativo deve permanecer no disco local. O OneDrive pode receber backups fechados e
verificados, mas não deve sincronizar o arquivo de banco enquanto ele está aberto.

Os arquivos `.ics` não inserem eventos silenciosamente em uma conta: o usuário confirma a
importação no calendário escolhido. A integração automática com calendário e e-mail será feita
somente após o módulo de login, por autorização segura (OAuth), sem armazenar senhas de e-mail.

## Documentação

- [Regras de negócio](docs/BUSINESS_RULES.md)
- [Arquitetura](docs/ARCHITECTURE.md)
- [Guia de desenvolvimento](docs/DEVELOPMENT.md)
- [Validação manual da v0.4.0](docs/MANUAL_TEST_V040.md)
- [Histórico de versões](CHANGELOG.md)

## Aviso normativo

O sistema auxilia a aplicação das regras configuradas, mas não substitui a leitura da norma,
os procedimentos internos do laboratório ou a avaliação técnica responsável. Toda alteração
normativa deverá gerar uma nova versão explícita das regras e seus respectivos testes.
