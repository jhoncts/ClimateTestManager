# Regras de negócio

## Fonte normativa

- Norma informada pelo laboratório: **ABNT NBR IEC 60079-0:2020**.
- Referência utilizada nesta etapa: Tabela 17 fornecida para o projeto.
- Cálculo da temperatura de serviço: `Ts = Tamb máxima + ΔT máximo`.
- Quando o cliente não informar a Tamb máxima, adotar `+40 °C`, conforme a Tabela 1 da
  ABNT NBR IEC 60079-0:2020.

O formulário deve informar explicitamente quando `+40 °C` estiver sendo adotado. O valor efetivo
deve ser persistido no ensaio e a origem desse valor deve constar no evento inicial de auditoria.

## Dados do cadastro

- A Marcação Ex não é solicitada.
- O processo é um identificador obrigatório de conteúdo livre, limitado a 10 caracteres na tela.
- A quantidade de amostras é obrigatória, deve ser um inteiro entre `1` e `99` e não aceita zero
  à esquerda na tela.
- Tamb e Delta T aceitam somente conteúdo numérico, com vírgula como separador visual.
- Um ponto digitado como separador decimal deve ser convertido imediatamente para vírgula.
- As permanências devem exibir horas, dias nominais e o limite superior incluindo a tolerância.

Os valores calculados deverão ser armazenados como fotografia da regra usada no cadastro.
Uma atualização futura da norma não deverá alterar retroativamente ensaios já registrados.

### Origem da condição

O cadastro apresenta somente três formas de definição:

| Origem | Dados necessários | Resultado |
| --- | --- | --- |
| Calculada por Tamb + ΔT | EPL, Tamb, ΔT e opção | Calcula Ts e consulta a Tabela 17 |
| Ts informado | EPL, Ts e opção | Consulta a Tabela 17 sem exigir Tamb ou ΔT |
| Personalizado | Temperatura, umidade, duração e secagem opcional | Não exige Ts, EPL ou opção quando esses dados não existem |

No modo personalizado, temperatura e umidade aceitam somente números entre `0` e `100`,
inclusive. A duração é um inteiro positivo em horas e não possui limite máximo definido pela
aplicação. O seletor **O plano exige secagem** determina se a segunda etapa deve ser informada.
Valores legados chamados `Critério do plano` ou `Configuração direta` são migrados para
`Personalizado` sem apagar a configuração já armazenada.

## Grupos de EPL

| Grupo | EPLs |
| --- | --- |
| Grupo 1 | Ga, Gb, Da, Db, Ma e Mb |
| Grupo 2 | Gc e Dc |

## Grupo 1 — Ga, Gb, Da, Db, Ma e Mb

| Faixa de Ts | Opção | Câmara climática | Secagem |
| --- | --- | --- | --- |
| `Ts ≤ 70 °C` | A | 672 h; 90 ± 5% UR; `máx(Ts + 20 K, 80 °C) ± 2 K` | Não aplicável |
| `70 °C < Ts < 75 °C` | A | 672 h; 90 ± 5% UR; `Ts + 20 K ± 2 K` | Não aplicável |
| `70 °C < Ts < 75 °C` | B | 504 h; 90 ± 5% UR; `90 °C ± 2 K` | 336 h; `Ts + 20 K ± 2 K` |
| `Ts ≥ 75 °C` | A | 336 h; 90 ± 5% UR; `95 °C ± 2 K` | 336 h; `Ts + 20 K ± 2 K` |
| `Ts ≥ 75 °C` | B | 504 h; 90 ± 5% UR; `90 °C ± 2 K` | 336 h; `Ts + 20 K ± 2 K` |

### Interpretação de Ts igual a 75 °C

Por orientação do laboratório, `Ts = 75 °C` utiliza as condições apresentadas na linha
`Ts > 75 °C`. No código, isso é representado explicitamente como `Ts ≥ 75 °C`.

## Grupo 2 — Gc e Dc

| Faixa de Ts | Opção | Câmara climática | Secagem |
| --- | --- | --- | --- |
| `Ts ≤ 80 °C` | A | 672 h; 90 ± 5% UR; `Ts + 10 K ± 2 K` | Não aplicável |
| `80 °C < Ts ≤ 85 °C` | A | 672 h; 90 ± 5% UR; `Ts + 10 K ± 2 K` | Não aplicável |
| `80 °C < Ts ≤ 85 °C` | B | 336 h; 90 ± 5% UR; `90 °C ± 2 K` | 336 h; `Ts + 10 K ± 2 K` |
| `Ts > 85 °C` | A | 336 h; 90 ± 5% UR; `95 °C ± 2 K` | 336 h; `Ts + 10 K ± 2 K` |
| `Ts > 85 °C` | B | 504 h; 90 ± 5% UR; `90 °C ± 2 K` | 336 h; `Ts + 10 K ± 2 K` |

Para Gc e Dc, não é aplicado o mínimo de 80 °C que aparece na primeira faixa do Grupo 1.

## Tolerâncias

- Temperatura da câmara e da secagem: `± 2 K`.
- Umidade relativa: `90 ± 5% UR`.
- Cada período indicado em horas possui tolerância de `+30/0 h`.

O sistema deverá manter separados:

- horário nominal de saída;
- horário máximo permitido;
- horário real registrado pelo operador.

Quando houver secagem, a saída deverá ser recalculada a partir do início real dessa etapa.

## Situação e condição

Situação descreve onde o ensaio está no fluxo:

- Aguardando
- Na Câmara
- Em Secagem
- Finalizado
- Cancelado

Condição descreve o prazo da próxima ação necessária:

- No prazo
- Vence hoje
- Em tolerância
- Atrasado

O término nominal abre a janela operacional de retirada. A condição permanece `Em tolerância`
até o horário máximo, inclusive. Somente após ultrapassar o limite nominal + 30 h o ensaio passa
a `Atrasado`.

## Fluxo operacional

- A câmara pode ser iniciada no horário atual ou em um horário real informado manualmente.
- A secagem não pode começar antes do término nominal da câmara.
- Quando houver secagem, seus prazos são calculados pelo início real dessa etapa.
- Ensaios sem secagem podem ser finalizados após o término nominal da câmara.
- O cancelamento exige motivo e preserva todos os eventos anteriores.
- Cadastros aguardando podem ser excluídos permanentemente após confirmação.
- Depois que a câmara é iniciada, o ensaio não pode ser apagado; uma desistência deve ser
  cancelada com motivo.
- Dados cadastrais podem ser corrigidos com justificativa. Mudanças térmicas recalculam os
  prazos da etapa ativa e preservam os valores anteriores no registro de atividades.
- Uma correção posterior não pode criar uma etapa de secagem incompatível com o fluxo que já foi
  concluído.
- Toda ação humana da v0.5.0 recebe o nome completo e o usuário da conta autenticada.
- Eventos importados de versões anteriores permanecem com o ator `Não identificado`; essa
  informação histórica não deve ser reescrita.
- Entrada e saída da câmara climática e entrada e saída da câmara seca são quatro registros
  independentes. Cada horário já registrado pode ser corrigido com nova data/hora e motivo.
- A escolha do registro deve apresentar explicitamente a etapa e o tipo de movimento; corrigir a
  entrada da câmara seca nunca pode alterar a entrada da câmara climática.
- A ordem cronológica deve permanecer: entrada climática, saída climática, entrada seca e saída
  seca. Uma correção que inverta essa sequência é recusada.
- Corrigir uma entrada recalcula o prazo nominal e máximo da etapa correspondente. Corrigir uma
  saída ajusta apenas o registro real; se o ensaio estiver finalizado, a saída final também
  atualiza o horário de conclusão.
- Toda correção preserva valor anterior, valor novo, motivo, responsável e horário na auditoria.
- Justificativas operacionais usam alternativas predefinidas. A opção `Outros` libera um campo de
  texto com no máximo 180 caracteres; texto livre ilimitado não é aceito pelo serviço.
- Antes de confirmar a entrada atual ou manual, o sistema apresenta entrada, retirada nominal e
  limite com tolerância em cartões separados, com dia da semana, data e hora.
- Quando a retirada nominal ou o limite cair no sábado ou domingo, o diálogo destaca **FIM DE
  SEMANA** e orienta a conferir a disponibilidade da equipe antes de registrar a entrada.
- Um cadastro novo ainda não salvo permanece como rascunho enquanto o usuário navega para outra
  tela na mesma execução do aplicativo.

## Pausa e retomada dos equipamentos

- Câmara climática e secagem possuem controles globais independentes no Dashboard.
- Pausar exige motivo e afeta todos os ensaios que estiverem naquele equipamento no instante.
- A barra de progresso usa somente tempo efetivamente cumprido; o período parado é descontado.
- Durante uma pausa, o progresso fica congelado e os avisos do ensaio não são entregues.
- A retomada encerra o intervalo e desloca os prazos nominal e máximo pelo tempo exato parado.
- Um equipamento pausado não aceita início, avanço ou finalização de etapa.
- Cadastros ainda aguardando não são alterados pela pausa, mas também não podem iniciar a câmara
  enquanto ela estiver indisponível.
- Cancelar um ensaio pausado continua permitido e preserva o motivo da parada e do cancelamento.

## Dashboard e agenda

- O Dashboard mostra somente `Aguardando`, `Na Câmara`, `Em Secagem` e os ensaios pausados nessas
  etapas. Finalizados e cancelados permanecem na tela **Ensaios**.
- Os quatro indicadores do Dashboard filtram a própria lista ao serem clicados; um segundo clique
  remove o filtro.
- Cada linha ativa usa uma barra compacta de progresso da etapa atual.
- A Agenda interna apresenta retirada nominal e limite máximo dos ensaios ativos em visão mensal.
- Durante uma pausa, a agenda mostra projeções que acompanham o tempo parado; ao retomar, os
  horários recalculados tornam-se definitivos.
- A Agenda interna é a referência operacional; a interface não envia eventos a calendários
  externos.

## Avisos

- Ao iniciar uma etapa, são agendados avisos para duas horas antes do término nominal e para o
  limite máximo, quando a condição passa a `Atrasado`.
- Cada aviso e cada canal possuem marcações persistidas para não serem entregues duas vezes.
- Quando o SMTP está habilitado, o e-mail é enviado a todas as contas ativas e contém cliente,
  produto, processo e quantidade de amostras.
- O agente local pode executar com a janela principal fechada.
- A tarefa agendada chama diretamente `ClimateTestNotifier.exe` ou `pythonw.exe`; ela não abre
  PowerShell ou CMD durante as verificações periódicas.
- O computador precisa estar ligado e com uma sessão do Windows iniciada.
- A configuração SMTP é restrita ao administrador. A senha fica protegida pelo Windows e não é
  gravada em texto aberto.
- A configuração e o Guia de uso apresentam modelos para Gmail, Microsoft 365 e outro provedor,
  além do fluxo para salvar, testar o envio e ativar o agente em segundo plano.
- O teste SMTP envia aos usuários ativos e também ao remetente configurado, mostra os
  destinatários aceitos e o identificador da mensagem. A cópia ao remetente existe somente para
  diagnóstico; os avisos automáticos continuam destinados às contas ativas.

## Usuários e segurança

- O banco sem usuários abre somente a configuração do primeiro acesso.
- A primeira conta é obrigatoriamente `Administrador`.
- O login aceita nome de usuário ou e-mail sem diferenciar letras maiúsculas e minúsculas.
- Usuários e e-mails são únicos.
- A senha possui no mínimo oito caracteres, pelo menos uma letra e um número.
- Senhas são armazenadas somente como PBKDF2-HMAC-SHA256 com salt individual.
- `Administrador` cria, corrige, ativa, desativa e redefine senhas de contas.
- `Operador` usa todas as funções técnicas, mas não administra usuários.
- O sistema sempre mantém pelo menos um administrador ativo.
- A v0.5.0 não diferencia um administrador principal dos demais administradores. A transferência
  formal dessa condição está planejada para uma versão futura.
- Um usuário não pode desativar a própria conta.
- A opção **Manter conectado** cria uma sessão revogável por 30 dias.
- Alteração ou redefinição de senha e desativação revogam as sessões existentes.
- O primeiro acesso apresenta uma central curta de ajuda. O conteúdo permanece acessível em
  **Guia de uso**, organizado por tarefas, e as telas usam balões `?` para explicações rápidas.
- A foto do perfil é opcional, limitada a 2 MB e aceita PNG, JPG ou WEBP.

## Backup

- Antes de criar o primeiro administrador, o responsável escolhe a pasta local do banco e pode
  indicar uma pasta externa para as cópias automáticas.
- O banco SQLite ativo permanece em disco local e não deve ser sincronizado aberto pelo OneDrive.
- OneDrive, Dropbox, Google Drive, iCloud e pastas de rede são recusados como local do banco
  ativo.
- Na abertura, o sistema tenta criar o backup diário antes da migração e garante uma cópia após
  inicializar um banco novo.
- A retenção automática conserva as 30 cópias diárias mais recentes em cada destino.
- Quando configurado, o OneDrive recebe uma segunda cópia diária consistente; o notificador
  também executa essa verificação quando a janela principal está fechada.
- Somente administradores podem alterar pela interface a pasta das cópias automáticas.
- O botão de backup manual gera uma cópia SQLite consistente e permite escolher o OneDrive.
- Cada backup automático precisa ser reaberto em modo somente leitura, aprovado por
  `quick_check` e `foreign_key_check` e acompanhado por manifesto SHA-256.
- Se a cópia diária estiver corrompida, ela é substituída por uma nova cópia consistente; o banco
  ativo não é substituído nessa operação.
- O banco ativo precisa passar por `quick_check` antes de migrações; em caso de falha, a abertura
  é bloqueada e o usuário deve restaurar uma cópia verificada.

## Falhas do sistema

- Qualquer usuário autenticado pode escolher um motivo controlado e registrar uma descrição breve
  e a ação tomada ao reconhecer a falha.
- A prioridade é atribuída automaticamente pelo catálogo do sistema; o usuário não pode
  reclassificá-la durante o relato.
- O motivo **Outros** permanece disponível e exige a mesma descrição e ação tomada.
- A falha aparece na central interna e no e-mail somente dos administradores ativos. Avisos de
  prazos e operações continuam disponíveis a todos os usuários ativos.
- O relato e a ação imediata originais não podem ser substituídos durante o encerramento.
- Somente Administrador pode encerrar uma falha, registrando ação corretiva, responsável e data.
- Uma falha com possível impacto em ensaio ou resultado precisa ser tratada também pelo
  procedimento de trabalho não conforme do laboratório; o registro no software não decide a
  aceitabilidade do resultado.
- Uma cópia só deve ser restaurada com o aplicativo e o notificador fechados.
