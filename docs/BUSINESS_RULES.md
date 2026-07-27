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
- A quantidade de amostras é obrigatória e deve ser um inteiro maior que zero.
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
- Até existir login, ações humanas recebem o ator `Não identificado`; o nome do usuário do Windows
  não é usado como identidade do responsável.
- A entrada registrada da câmara pode ser corrigida com nova data/hora e motivo obrigatório.
  O sistema recalcula os prazos e preserva os dois valores na auditoria.

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
- Cada linha ativa usa uma barra compacta de progresso da etapa atual.
- A Agenda interna apresenta retirada nominal e limite máximo dos ensaios ativos em visão mensal.
- Durante uma pausa, a agenda mostra projeções que acompanham o tempo parado; ao retomar, os
  horários recalculados tornam-se definitivos.
- O arquivo `.ics` continua disponível como exportação manual de um ensaio iniciado.

## Avisos

- Ao iniciar uma etapa, são agendados avisos para o término nominal e para o limite máximo.
- Cada aviso possui uma chave persistida para não ser exibido duas vezes.
- O agente local pode executar com a janela principal fechada.
- A tarefa agendada chama diretamente `ClimateTestNotifier.exe` ou `pythonw.exe`; ela não abre
  PowerShell ou CMD durante as verificações periódicas.
- O computador precisa estar ligado e com uma sessão do Windows iniciada.
- E-mail e calendário automáticos dependem do futuro login e de consentimento seguro da conta.
