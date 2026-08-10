# Histórico de versões

Todas as mudanças relevantes deste projeto serão registradas neste arquivo.

O formato segue o princípio do [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o projeto utiliza versionamento semântico.

## [Não publicado]

### v0.6.0 — rede local, central de notificações e identidade própria

- Servidor Flet para acesso simultâneo por computadores e celulares na rede privada, mantendo o
  SQLite exclusivamente no computador servidor.
- Assistente inicial e recuperação do administrador limitados ao navegador local do servidor.
- Código de recuperação de uso único, rotação obrigatória e revogação das sessões anteriores.
- Central interna com leitura individual; avisos operacionais para todos e falhas somente para
  administradores.
- Catálogo de motivos de falha com prioridade automática, descrição e ação adotada obrigatórias.
- Fila idempotente de e-mails de falha destinada somente aos administradores ativos.
- E-mails HTML responsivos e notificações do Windows com nova identidade visual.
- Logo exclusiva do ClimateTest Manager em PNG e ICO, preparada como base de uma família de
  softwares laboratoriais.
- Instalador do servidor com tarefas automáticas, regra de firewall privada, atalho e dados fora
  de `Program Files`.
- Workflow de release que testa, cria os executáveis, compila o instalador e o publica com a tag.

### Corrigido

- O estado dos avisos em segundo plano agora considera se a tarefa do Windows está realmente
  habilitada, inclusive quando a saída do Agendador declara UTF-16 com bytes em outra codificação
  ou omite o valor padrão `Enabled=true`, evitando estados incorretos na interface.

### Adicionado

- Primeiro acesso guiado para criação obrigatória do administrador inicial.
- Cadastro local de usuários com nome, sobrenome, usuário único, e-mail e perfil.
- Perfis `Administrador` e `Operador`, com gerenciamento de contas restrito ao administrador.
- Login por nome de usuário ou e-mail e opção de permanecer conectado por 30 dias.
- Sessões locais revogáveis; apenas o resumo SHA-256 do token fica no banco.
- Senhas protegidas com PBKDF2-HMAC-SHA256, salt individual e 600 mil iterações.
- Alteração da própria senha, redefinição administrativa e encerramento das sessões anteriores.
- Proteção contra desativação própria e remoção do último administrador ativo.
- Identificação real do responsável em todas as atividades técnicas da v0.5.0.
- Trilha separada para eventos de segurança e administração de contas.
- Guia orientado a tarefas, com instruções para cadastrar, editar, cancelar, registrar horários,
  pausar equipamentos e criar usuários.
- Balões de ajuda contextual `?` nas áreas técnicas e operacionais.
- Foto de perfil opcional em PNG, JPG ou WEBP, preservada junto com o banco e seus backups.
- Rascunho temporário do novo ensaio enquanto o usuário consulta outra tela.
- Filtros clicáveis nos indicadores do Dashboard.
- Avisos por e-mail para todos os usuários ativos duas horas antes da retirada nominal e quando o
  ensaio entra em atraso.
- Crédito clicável `Created by Jhoncts`, com acesso ao perfil do GitHub.
- Backup SQLite automático diário com retenção local das 30 cópias mais recentes.
- Manual de validação da v0.5.0, cobrindo migração, acesso, perfis, auditoria e distribuição.
- Faixas responsivas para navegação, margens, cartões, listas, formulários, imagens e ícones,
  preservando a tela aberta durante o redimensionamento.
- Motivos predefinidos para pausa, cancelamento e correções, com opção `Outros` limitada a 180
  caracteres.
- Tutorial de configuração SMTP disponível na própria janela e no Guia de uso.
- Comprovante do teste SMTP com destinatários aceitos e identificador da mensagem.
- Confirmações antes de sair da conta, descartar um novo ensaio, remover a foto, desativar os
  avisos e avançar entre etapas operacionais.
- Assistente inicial para o responsável escolher a pasta local dos dados e uma pasta externa de
  backup antes da criação do primeiro administrador.
- Segunda cópia diária automática em OneDrive ou outro destino externo configurado, mantendo 30
  arquivos em cada local.
- Destaque do dia da semana na entrada, retirada nominal e limite com tolerância, com alerta de
  fim de semana para apoiar o planejamento da equipe.
- Botão para recolher e expandir a barra lateral em telas largas, preservando ícones, dicas,
  conteúdo e posição de rolagem.
- Manifesto de cada backup automático com SHA-256, tamanho, versão do esquema, `quick_check` e
  conferência de integridade referencial.
- Registro auditável de falhas do sistema, contenção imediata e ação corretiva de encerramento.
- Dossiê de conformidade com matriz da ABNT NBR ISO/IEC 17025:2017, protocolo de validação,
  procedimento do sistema computadorizado e avaliação de riscos.
- Identificação explícita, em Configurações, das normas e referências consideradas no projeto.

### Alterado

- Ações operacionais passam a exibir separadamente `Registrar com o horário atual` e
  `Informar outro horário`.
- Configurações passam a reunir conta, alteração de senha, guia e acesso à administração.
- Login, primeiro acesso e diálogo de usuários recebem novo layout sem campos sobrepostos.
- Transições de tela e barra de rolagem recebem tratamento visual mais leve.
- Quantidade de amostras passa a aceitar somente valores de `1` a `99`, sem zero à esquerda.
- A confirmação da entrada na câmara mostra entrada, retirada nominal e limite com tolerância.
- A Agenda interna passa a ser a referência única; a ação de adicionar a calendários externos foi
  removida da interface.
- Ativação das notificações cria a tarefa diretamente com `schtasks.exe`, inclusive no pacote,
  sem depender da pasta do projeto ou de um processo PowerShell.
- Empacotamento gera uma pasta de distribuição e um ZIP versionado com aplicativo, notificador e
  instruções.
- Banco atualizado de forma não destrutiva para o esquema 11, preservando todos os ensaios da
  v0.4.0.
- Ações operacionais recebem hierarquia visual mais clara entre operação em tempo real e registro
  posterior, com explicação do efeito na rastreabilidade.
- Resumo do ensaio reorganizado com o `Ts` em destaque, equação térmica visível e informações
  secundárias agrupadas por identificação, situação, prazo e progresso.
- Formulário de ensaio reorganizado em colunas responsivas, com identificação, observações,
  configuração térmica e prévia calculada em blocos visualmente distintos.
- Condições da câmara e da secagem passam a reunir parâmetros e cronograma em cartões próprios,
  lado a lado quando houver largura e empilhados em janelas menores.
- Ações de horário atual e registro manual recebem cartões equivalentes; cancelamento e histórico
  técnico passam a ocupar toda a largura útil.
- Diálogos de criação e edição de usuários passam a usar uma grade compacta, cabeçalho contextual
  e ação principal destacada.
- Cabeçalho do ensaio passa a destacar `Cliente / processo`, mantendo `Ensaio #N` como informação
  secundária.
- Entrada e saída da câmara climática e da câmara seca passam a ser corrigidas separadamente, com
  validação cronológica e recálculo apenas dos prazos dependentes de uma entrada.
- Diálogos operacionais recebem cabeçalho, orientação, bordas, espaçamento e ações consistentes.
- O teste de e-mail envia também uma cópia diagnóstica ao remetente, sem alterar os destinatários
  dos avisos automáticos.
- O banco SQLite ativo é recusado em OneDrive, outros sincronizadores e pastas de rede; somente
  cópias consistentes e fechadas são enviadas ao destino externo.

### Corrigido

- Barra de rolagem sobrepondo a lateral do botão **Salvar ensaio**.
- Botão temporário de avanço aparecendo sem callback funcional; agora ele só é exibido quando o
  modo explícito de validação está ativo.
- Perda dos dados digitados ao sair temporariamente da tela **Novo ensaio**.
- Repetição do aviso de um canal quando o outro canal falha; cada entrega possui controle
  independente.
- Texto escuro e mensagens extrapolando os cartões da lateral de acesso.
- Cartões e ações desalinhados ao reduzir ou ampliar a janela.
- Blocos cinza no controle dos equipamentos, no registro de atividades, nos usuários, na Agenda
  e nas ações do ensaio, causados por filhos expansíveis dentro de linhas com quebra automática.
- Tela de detalhes exibindo somente o cabeçalho porque o alinhamento `STRETCH` tentava impor
  altura infinita ao primeiro bloco responsivo dentro da área rolável.
- Rolagem voltando ao topo quando pequenas oscilações de largura reconstruíam a moldura perto de
  um breakpoint; a posição agora é preservada e as faixas possuem margem de estabilidade.
- Textos dos botões **Pausar** e **Retomar** quebrando no meio das palavras em cartões estreitos.
- Serrilhado na borda da foto de perfil e do símbolo do GitHub, com recorte antialias e
  filtragem de maior qualidade.
- Tipografia borrada durante redimensionamentos animados; a interface usa a fonte nativa Segoe UI
  no Windows e não anima mais o tamanho de cartões ou da área principal.
- Campos de observações, ações operacionais e histórico técnico ficando estreitos no canto
  esquerdo mesmo quando havia espaço disponível.
- Permanências, identificação e informações secundárias cortadas com reticências em cartões
  estreitos; os textos importantes agora quebram linha e usam a largura disponível.
- Flash ocasional e retorno ao topo causados por atualizações integrais do formulário e transições
  de opacidade; somente os controles dinâmicos são atualizados e a troca de tela não anima.
- Senha SMTP antiga definida no ambiente substituindo a senha protegida salva pela interface.
  A credencial protegida agora é prioritária e senhas de app do Gmail têm os separadores visuais
  removidos automaticamente.
- Erro técnico de codificação ao autenticar uma credencial SMTP com acento; a interface agora
  orienta a informar novamente o usuário ou a senha de app.
- Falha de codificação antes da autenticação SMTP quando o nome do computador Windows continha
  acento; o comando `EHLO` agora usa uma identificação local ASCII estável.
- Teste de e-mail declarando sucesso sem mostrar os endereços utilizados ou analisar
  destinatários recusados pelo servidor; o envelope SMTP agora é explícito e a aceitação fica
  verificável na interface.

### Segurança

- Nenhuma senha de usuário ou senha SMTP é armazenada em texto aberto.
- A senha SMTP é protegida pelo Windows e a configuração só pode ser alterada por administrador.
- Mensagem de login não revela se o usuário/e-mail existe.
- Identidades são comparadas sem diferenciar maiúsculas e minúsculas para impedir duplicidade.
- Conta desativada perde suas sessões persistentes imediatamente.

## [0.4.0] - 2026-07-28

### Adicionado

- Controle operacional das etapas de câmara e secagem com horários reais.
- Saídas nominal e máxima, mantendo a tolerância positiva de 30 horas visível.
- Condição de prazo `Em tolerância`; atraso somente depois do limite máximo.
- Início imediato ou registro manual de data e hora.
- Finalização e cancelamento auditável com motivo obrigatório.
- Tela de ensaios com pesquisa, filtro e acesso aos detalhes.
- Histórico por ensaio e consulta global dos eventos.
- Exportação CSV dos ensaios e arquivo de calendário no formato ICS.
- Notificações nativas do Windows com entrega persistente e sem duplicidade.
- Tarefa agendada configurável para avisar mesmo com a janela principal fechada.
- Migração idempotente dos bancos SQLite criados nas versões anteriores.
- Modo WAL, tempo de espera e proteção para acesso simultâneo do aplicativo e notificador.
- Três formas objetivas de definir a condição: cálculo por Tamb + ΔT, Ts informado e
  Personalizado.
- Quantidade de amostras no cadastro, nos resumos, nos avisos e na exportação.
- Correção auditável dos dados antes, durante ou depois da execução.
- Exclusão permanente somente para cadastros ainda não iniciados, com confirmação.
- Linha visual das etapas do ensaio e registro global renomeado para `Atividades`.
- Escolha do arquivo de destino ao exportar os resultados filtrados em CSV.
- Cópia consistente do banco SQLite com escolha do local de destino.
- Diagnóstico do notificador: banco monitorado, última verificação e notificação de teste.
- Pausa e retomada independentes da câmara climática e da secagem, com motivo obrigatório.
- Congelamento do progresso e recálculo automático de todos os prazos afetados pelo tempo parado.
- Barra compacta de progresso por ensaio ativo no Dashboard.
- Agenda mensal interna com retirada nominal, limite máximo e projeção durante pausas.
- Correção auditável da data e hora de entrada na câmara.
- Temas claro e escuro com preferência local persistida.
- Botão temporário de avanço de etapa, disponível somente com variável explícita de validação.
- Quantidade de amostras pode ser apagada e substituída sem prender o valor inicial `1`.
- Digitação de datas e horas aplica automaticamente as máscaras `DD/MM/AAAA` e `HH:MM`, com
  limite de tamanho e validação antes de confirmar.

### Alterado

- Ações humanas são registradas como `Não identificado` até a implementação do login.
- Dashboard passa a mostrar somente pendentes, pausados e em andamento; finalizados e cancelados
  permanecem na tela Ensaios.
- Empacotamento passa a gerar o aplicativo e o notificador na versão 0.4.0.
- Horários passam a usar nomes operacionais: `Entrada registrada`, `Retirada recomendada`,
  `Último prazo permitido` e `Retirada registrada`.
- A tarefa agendada chama diretamente um executável sem console ou `pythonw.exe`, sem abrir
  CMD/PowerShell a cada verificação.
- Valores inexistentes nos cadastros simplificados deixam de aparecer como Ts, EPL ou opção
  fictícios.
- Os antigos modos de critério do plano e configuração direta são apresentados como
  `Personalizado`; temperatura e umidade personalizadas ficam limitadas de 0 a 100.
- Avisos de um ensaio pausado deixam de ser entregues até a retomada e o reagendamento.

### Corrigido

- Falha ao cancelar causada pela ausência do callback `_on_cancel` em `TestDetailsView`.
- Desalinhamento dos resumos técnicos na dashboard quando cliente ou condição possuem textos
  de tamanhos diferentes.
- Reagendamento de notificações após uma correção de dados sem violar a chave única do SQLite.

## [0.3.0] - 2026-07-22

### Adicionado

- Conversão operacional das permanências em dias nominais e limite com tolerância.
- Normalização imediata das entradas decimais para o padrão brasileiro.
- Filtros que removem caracteres não numéricos de Tamb e Delta T.

### Alterado

- Exemplo do processo atualizado para `26123.1`, com limite de 10 caracteres, conteúdo livre e
  contador oculto para preservar o alinhamento da tela.
- Valores decimais apresentados com vírgula na interface.
- Mensagem do dashboard esclarece a persistência local e as regras versionadas da Tabela 17.

### Removido

- Campo Marcação Ex da tela e do caso de uso de cadastro; somente o EPL é necessário para a
  determinação das condições climáticas.

## [0.2.1] - 2026-07-21

### Corrigido

- Liberação explícita da conexão SQLite ao fechar a aplicação.
- Limpeza dos bancos temporários nos testes executados no Windows.
- Exibição de valores inteiros terminados em zero, como 90 °C, 90% UR e Ts de 140 °C.

### Alterado

- Integração contínua executada em Linux e Windows para detectar diferenças entre plataformas.
- Tamb máxima passa a adotar +40 °C, de forma visível e auditável, quando não informada pelo
  cliente.

## [0.2.0] - 2026-07-21

### Adicionado

- Formulário profissional de cadastro de ensaios.
- Cálculo interativo de Ts e das condições da Tabela 17.
- Escolha do operador entre as opções A e B quando ambas são válidas.
- Leitura de ponto ou vírgula como separador decimal.
- Persistência da fotografia normativa aplicada a cada ensaio.
- Registro automático do evento de criação na auditoria.
- Dashboard conectado aos cadastros recentes.
- Navegação funcional entre dashboard e novo ensaio.
- Testes integrados do serviço, banco e montagem da aplicação.

## [0.1.0] - 2026-07-21

### Adicionado

- Estrutura profissional baseada no padrão `src`.
- Janela desktop inicial em Flet.
- Configuração local do SQLite na pasta de dados do usuário.
- Modelos iniciais de ensaio e evento de auditoria.
- Motor da Tabela 17 com opções A e B.
- Interpretação operacional de `Ts = 75 °C` na faixa superior.
- Testes unitários das principais fronteiras normativas.
- Configuração de Pytest, Ruff e integração contínua.
- Script de empacotamento para Windows com PyInstaller.
