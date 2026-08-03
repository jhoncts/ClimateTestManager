# ClimateTest Manager

Aplicação desktop para controle de ensaios de resistência climática realizados conforme a
**ABNT NBR IEC 60079-0:2020**.

O projeto nasce para substituir uma planilha operacional por um software local, auditável e
preparado para gerar um executável do Windows sem abrir navegador ou terminal.

> Status: versão 0.5.0 candidata à implantação controlada. O fluxo técnico, autenticação,
> rastreabilidade, notificações, agenda e backups estão funcionais. A adoção oficial ainda deve
> seguir a validação interna e os procedimentos do laboratório.

## Funcionalidades disponíveis

- Cadastro de ensaios climáticos com validação dos campos obrigatórios.
- Cadastro por três formas: Tamb + ΔT, Ts informado ou condição personalizada.
- Quantidade de amostras limitada de `1` a `99` e acompanhada em todas as etapas.
- Cálculo de `Ts = Tamb + ΔT`.
- Consulta automática das condições da Tabela 17.
- Escolha entre as opções A e B quando ambas forem permitidas.
- Normalização das entradas decimais para vírgula e bloqueio de caracteres não numéricos.
- Apresentação das permanências em horas, dias nominais e limite com tolerância.
- Gravação local do ensaio, da condição normativa e do primeiro evento de auditoria.
- Dashboard restrito aos ensaios pendentes, pausados e em andamento, com progresso compacto e
  indicadores clicáveis que funcionam como filtros.
- Início da câmara no horário atual ou em data/hora informada manualmente.
- Cálculo separado da saída nominal e do limite máximo com tolerância de `+30 h`.
- Confirmação da entrada com cartões grandes para entrada, retirada nominal e limite, incluindo
  o dia da semana e um alerta quando um prazo cair no sábado ou domingo.
- Condição `Em tolerância` entre a saída nominal e o limite máximo; atraso somente após o limite.
- Início da secagem pelo horário real de retirada da câmara e recálculo dos respectivos prazos.
- Pausa global e independente da câmara climática e da secagem, com congelamento da contagem,
  motivo obrigatório e deslocamento automático dos prazos na retomada.
- Correção auditável e independente da entrada e da saída da câmara climática e da câmara seca,
  com validação da ordem cronológica e recálculo dos prazos quando uma entrada é alterada.
- Finalização, cancelamento, pausa e correções com motivos rápidos; a opção `Outros` abre um campo
  limitado a 180 caracteres.
- Correção auditável dos dados e exclusão somente de cadastros não iniciados.
- Lista pesquisável com filtro de situação e tela completa de detalhes.
- Caminho visual do ensaio e registro global de atividades.
- Agenda mensal interna para retirada nominal e limite máximo dos ensaios ativos.
- Exportação dos resultados filtrados em CSV com escolha do local.
- Avisos nativos do Windows executados silenciosamente a cada 5 minutos, mesmo com a janela
  principal fechada.
- Tela de Configurações com teste de notificação, última verificação, pasta dos dados e cópia de
  segurança do banco.
- Temas claro e escuro com preferência preservada no computador.
- Migração automática e não destrutiva de bancos criados pela v0.3.0.
- Primeiro acesso guiado para criação do administrador inicial.
- Login por usuário ou e-mail e sessão persistente opcional por 30 dias.
- Senhas protegidas com PBKDF2 e salt individual; nenhuma senha é salva em texto aberto.
- Perfis de Administrador e Operador, com criação, correção, desativação e redefinição de senha.
- Nome real do responsável registrado em cada ação técnica.
- Sem autocadastro público: somente administradores criam contas autorizadas.
- Foto de perfil opcional, Guia de uso por tarefas e ajuda contextual nas telas.
- Rascunho do novo ensaio preservado ao consultar Agenda, Dashboard ou outra tela.
- Transições sem flash, preservação da rolagem e barra de rolagem menos intrusiva.
- Barra lateral recolhível em telas largas, mantendo ícones e dicas sem perder a tela aberta.
- E-mails automáticos para todos os usuários ativos duas horas antes da retirada nominal e no
  início do atraso.
- Confirmações antes de encerrar a sessão, descartar dados ou concluir ações operacionais
  importantes.
- Crédito clicável `Created by Jhoncts` no rodapé da navegação.
- Escolha inicial e consciente da pasta local dos dados pelo responsável pela instalação.
- Backup automático diário com retenção das 30 cópias locais mais recentes e uma segunda cópia
  em pasta externa ou OneDrive quando configurado; cada cópia automática recebe verificação
  SQLite, conferência de vínculos e manifesto SHA-256.
- Registro de falhas do sistema com impacto, ação imediata e encerramento administrativo por ação
  corretiva, preservando o relato original.
- Base normativa, versão da regra e ressalva de responsabilidade disponíveis em Configurações.
- Dossiê de conformidade com matriz ISO/IEC 17025, protocolo de validação, procedimento de ciclo
  de vida e avaliação de riscos.
- Pacote Windows com aplicativo, notificador silencioso e instruções.

## Próximas funcionalidades

- Preferências individuais de idioma, formatos e antecedência dos avisos.
- Assistente guiado de restauração das cópias de segurança.
- Transferência formal da condição de administrador principal para outra conta, com confirmação,
  auditoria e proteção contra perda de acesso.

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

O resultado será criado em `dist/ClimateTestManager-v0.5.0-windows.zip`. O comando usa
`flet pack`, a integração oficial do Flet com o PyInstaller, sem habilitar o console de
depuração. O pacote contém `ClimateTestManager.exe`, `ClimateTestNotifier.exe` e o manual de
primeiro uso.

## Primeiro acesso

Na primeira abertura, o responsável define:

- uma pasta local estável para o banco ativo;
- uma pasta de cópias de segurança no OneDrive, recomendada para proteger os dados se o
  computador falhar.

O banco aberto não pode ficar em OneDrive, Dropbox, Google Drive, iCloud ou pasta de rede. Depois
disso, o sistema solicita:

- nome e sobrenome;
- nome de usuário;
- e-mail;
- senha e confirmação.

Essa primeira conta será administradora. Depois do cadastro, o sistema apresenta um guia curto
organizado pelas tarefas do laboratório. Outros operadores são cadastrados manualmente em
**Usuários**; não existe criação pública de conta.

## Avisos em segundo plano

Na tela **Configurações**, selecione **Ativar avisos**. O sistema cria uma tarefa do Windows que
verifica os prazos a cada 5 minutos. A janela principal pode permanecer fechada, mas o computador
deve estar ligado e a sessão do Windows iniciada. A tarefa chama diretamente o notificador sem
abrir uma janela de CMD ou PowerShell.

Um administrador também pode configurar um servidor SMTP em **Configurações**. Quando ativado, o
mesmo agente envia um e-mail a todos os usuários ativos duas horas antes da retirada nominal e
quando o limite máximo é ultrapassado. A senha SMTP fica protegida pela conta do Windows.

### Configurar os avisos por e-mail

1. Entre como administrador e abra **Configurações → Avisos por e-mail → Configurar e-mail**.
2. Escolha **Gmail**, **Microsoft 365** ou **Outro provedor**. Os modelos conhecidos preenchem
   servidor, porta `587` e TLS.
3. Informe o e-mail remetente e o usuário SMTP; normalmente ambos são o endereço completo.
4. No Gmail, ative a verificação em duas etapas e gere uma senha de app para o sistema. Não use a
   senha normal da conta. Ela pode ser colada com os espaços exibidos pelo Google; o sistema
   remove esses separadores automaticamente.
5. No Microsoft 365 corporativo, confirme com a TI se o SMTP autenticado está permitido para a
   conta. Esta versão usa usuário e senha SMTP e não implementa OAuth2.
6. Ative **Enviar e-mails automáticos**, salve e clique em **Testar e-mail**. O teste vai para os
   usuários ativos e inclui uma cópia no próprio remetente para diagnóstico.
7. Ative também **Avisos em segundo plano**, pois é o agente local que verifica os prazos a cada
   5 minutos.

Quando o servidor aceita o teste, o sistema mostra os endereços usados e o identificador da
mensagem. Confira primeiro a caixa do remetente. Se a cópia chegar ao Gmail e não chegar ao
endereço corporativo, o envio do sistema está funcionando e a TI deve verificar filtro,
quarentena ou política de mensagens externas. Os avisos automáticos continuam sendo enviados
somente aos usuários ativos cadastrados.

O mesmo passo a passo fica disponível dentro da janela de configuração e no **Guia de uso**.
Se outro provedor for utilizado, solicite ao provedor ou à TI o servidor, a porta, o uso de TLS e
a credencial destinada ao sistema. Nunca inclua senhas reais em capturas ou relatórios.

O banco SQLite ativo permanece no disco local. O sistema cria um backup local por dia e mantém os
30 mais recentes. Quando o administrador configura uma pasta externa, outra cópia diária,
consistente e fechada é gravada no OneDrive, também com retenção de 30 arquivos. Cada cópia
automática recebe um arquivo `.manifest.json` com resultado da verificação SQLite, versão do
esquema, tamanho e SHA-256. O OneDrive não sincroniza o banco enquanto ele está aberto.

A Agenda interna é a referência para retiradas e limites; a operação normal não depende do
Outlook nem de outro calendário externo.

## Documentação

- [Regras de negócio](docs/BUSINESS_RULES.md)
- [Arquitetura](docs/ARCHITECTURE.md)
- [Guia de desenvolvimento](docs/DEVELOPMENT.md)
- [Validação manual da v0.5.0](docs/MANUAL_TEST_V050.md)
- [Dossiê de conformidade do sistema](docs/compliance/README.md)
- [Matriz ISO/IEC 17025 para o software](docs/compliance/ISO17025_SOFTWARE_COMPLIANCE_MATRIX.md)
- [Protocolo formal de validação](docs/compliance/VALIDATION_PROTOCOL_V050.md)
- [Procedimento de gestão do sistema](docs/compliance/DIGITAL_SYSTEM_OPERATION_PROCEDURE.md)
- [Avaliação de riscos](docs/compliance/RISK_ASSESSMENT_V050.md)
- [Histórico de versões](CHANGELOG.md)

## Aviso normativo

O sistema foi projetado para apoiar os requisitos aplicáveis da ABNT NBR ISO/IEC 17025:2017 e
as condições configuradas da ABNT NBR IEC 60079-0:2020. Isso não significa certificação do
produto nem acreditação automática do laboratório. O sistema não substitui a leitura da norma,
os procedimentos internos, a competência das pessoas, a validação no ambiente real ou a
avaliação técnica responsável. Toda alteração normativa deverá gerar análise de impacto, nova
versão explícita das regras, testes e aprovação antes do uso.
