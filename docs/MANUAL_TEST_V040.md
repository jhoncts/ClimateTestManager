# Validação manual da v0.4.0 no Windows

Use exclusivamente dados fictícios e um banco de demonstração separado. A versão ainda não é um
sistema oficial de controle operacional.

## Preparação

1. Confirme que está na branch `feat/v0.4.0-operational-control`; não publique nem crie tag.
2. Copie o banco de demonstração da v0.3.0 para uma nova pasta; nunca sobrescreva o original.
3. Defina `CLIMATETEST_DATA_DIR` para a pasta da v0.4.0.
4. Execute Ruff e Pytest antes de abrir a aplicação.

5. Para mostrar o controle temporário, defina
   `$env:CLIMATETEST_TEST_CONTROLS = "1"` antes de abrir o Flet.

Resultado automatizado de referência: **68 testes aprovados e 81% de cobertura**.

## Migração

Ao abrir a aplicação, confirme que os ensaios fictícios da v0.3.0 continuam no dashboard. A
abertura acrescenta campos operacionais ao banco copiado, sem alterar o banco original.

## Cenário de câmara e tolerância

Cadastre um ensaio fictício com opção B e permanência de 504 h. Na tela de detalhes:

1. Registre a entrada manual exatamente 21 dias antes do horário atual.
2. Confirme situação `Na Câmara` e condição `Em tolerância`.
3. Confirme saída nominal igual à entrada + 504 h.
4. Confirme limite máximo igual à saída nominal + 30 h.
5. Inicie a secagem e confirme que seus prazos usam o horário real dessa ação.

O sistema deve impedir o início da secagem quando a saída nominal da câmara ainda não chegou.

## Três formas de cadastrar a condição

Crie três ensaios fictícios separados e confira os detalhes:

1. **Calcular com Tamb + ΔT:** informe EPL, Tamb e ΔT; confirme o Ts calculado.
2. **Usar Ts informado:** deixe Tamb e ΔT vazios; informe somente Ts, EPL e a opção.
3. **Personalizado:** deixe Ts e EPL vazios e informe temperatura, umidade e duração da câmara;
   confirme a descrição `Condição personalizada` e teste o seletor de secagem.

Em todos os casos, confirme a quantidade de amostras no dashboard, na lista e nos detalhes.
No campo de quantidade, apague o valor inicial `1` com Backspace, digite `2` e confirme que o
resultado é `2`, não `12`.
No modo Personalizado, confirme que letras são rejeitadas, temperatura e umidade não aceitam
valores abaixo de 0 ou acima de 100, e a duração aceita um inteiro positivo grande.

## Dashboard, progresso e equipamentos

1. Confirme que o Dashboard mostra somente pendentes, pausados e em andamento.
2. Finalize e cancele ensaios fictícios e confirme que eles desaparecem do Dashboard, mas
   continuam em **Ensaios**.
3. Confirme que a barra de progresso é compacta e aumenta conforme o tempo efetivamente cumprido.
4. Use **Pausar** na Câmara climática, informe um motivo e confirme que todos os ensaios que
   estavam nela aparecem como pausados.
5. Confirme que a barra fica congelada, que iniciar outro ensaio é bloqueado e que o motivo aparece
   nos detalhes.
6. Avance o relógio de teste ou aguarde um intervalo conhecido; use **Retomar** e confirme que os
   prazos nominal e máximo aumentaram exatamente pelo tempo parado.
7. Repita o procedimento para **Secagem** e confirme que ensaios na câmara climática não são
   afetados.

## Entrada da câmara e avanço de teste

1. Em um ensaio iniciado, use **Alterar entrada da câmara**.
2. Apague os valores e digite `06072026` e `1430`; confirme a formatação automática
   `06/07/2026` e `14:30`.
3. Informe nova data/hora e motivo; confirme o recálculo dos prazos e os valores anterior e novo
   na atividade.
4. Com `CLIMATETEST_TEST_CONTROLS=1`, use **Teste: avançar etapa**.
5. Confirme a sequência `Aguardando → Na Câmara → Em Secagem → Finalizado` ou o encerramento
   direto quando não houver secagem.
6. Feche e reabra sem a variável; confirme que o botão de teste não aparece.

## Edição, exclusão e cancelamento

1. Crie um cadastro e, antes de iniciá-lo, use **Excluir cadastro**.
2. Confirme que a pergunta de segurança apresenta **Não** e **Sim, excluir**.
3. Crie outro ensaio, inicie a câmara e corrija cliente, produto, quantidade e dados térmicos.
4. Informe o motivo e confirme que os prazos da etapa ativa foram recalculados.
5. Verifique no registro técnico os valores anteriores, novos e o motivo.
6. Confirme que um ensaio iniciado não oferece exclusão permanente.
7. Use **Cancelar ensaio**, informe um motivo e confirme **Sim, cancelar**.
8. Confirme que o ensaio cancelado permanece na lista e no registro de atividades.

## Histórico e cancelamento

- Confirme os eventos `Ensaio cadastrado`, `Câmara iniciada` e `Secagem iniciada`.
- Confirme que ações humanas aparecem como `Não identificado` enquanto não há login.
- Em outro ensaio fictício, cancele com uma justificativa e confirme sua presença no histórico.

## Exportações

- Aplique uma pesquisa ou filtro, use **Exportar resultados (CSV)** e escolha nome e local.
- Abra o CSV e confirme que somente os resultados visíveis foram exportados.
- Confirme as colunas de origem da condição, quantidade, câmara, secagem e prazos.
- Em um ensaio iniciado, use **Adicionar à agenda** e confirme o evento de retirada e o alerta de
  duas horas no aplicativo de calendário escolhido.
- Em **Configurações**, use **Criar cópia de segurança**, escolha o destino e confirme que o
  arquivo `.db` foi criado.

## Agenda interna e tema

1. Abra **Agenda** e confirme o mês atual, os dias marcados e a lista do dia selecionado.
2. Confirme os dois horários de cada etapa ativa: **Retirar a partir de** e **Limite para
   retirada**.
3. Pause um equipamento e confirme que as datas aparecem como projeção; retome e confira os novos
   horários.
4. Em **Configurações**, alterne entre tema claro e escuro.
5. Feche e reabra o programa; confirme que o tema escolhido foi preservado.

## Aviso em segundo plano

1. Mantenha a tarefa antiga desativada.
2. Abra **Configurações** e use **Testar notificação**.
3. Ative os avisos somente depois que o teste aparecer.
4. Feche a janela principal.
5. Aguarde pelo menos 5 minutos e confirme que nenhuma janela de CMD ou PowerShell pisca.
6. Use um prazo nominal já vencido no banco de demonstração e confirme a notificação nativa.
7. Reabra o programa e confira a data/hora da última verificação e o banco monitorado.
8. Pause o equipamento antes de outro prazo fictício e confirme que nenhum aviso daquele ensaio
   é entregue durante a parada; retome e confira o prazo recalculado.
9. Confirme que os dados continuam presentes.

O computador precisa estar ligado e com a sessão iniciada. Ao terminar a validação, os avisos do
banco de demonstração podem ser desativados na mesma tela.

## Encerramento

Depois de fechar a aplicação, confira `git status` e confirme que somente as alterações planejadas
da v0.4.0 aparecem. O banco, as preferências, os arquivos CSV e os arquivos ICS ficam fora do
repositório Git.
