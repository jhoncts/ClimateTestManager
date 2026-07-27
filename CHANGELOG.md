# Histórico de versões

Todas as mudanças relevantes deste projeto serão registradas neste arquivo.

O formato segue o princípio do [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o projeto utiliza versionamento semântico.

## [Não publicado]

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

### Planejado

- Cadastro com e-mail, nome de usuário, nome, sobrenome, senha e confirmação de senha.
- Login por usuário ou e-mail, sessão persistente opcional e saída da conta.
- Tutorial inicial e ajuda resumida para cada função.
- Perfis e identificação do responsável.
- Integração autorizada com calendário e e-mail.

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
