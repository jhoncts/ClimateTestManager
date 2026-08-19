# ClimateTest Manager v0.8.6 — plano de implementação

Esta versão é um pacote de estabilidade, sincronização, refinamento visual e novo fluxo opcional de resistência térmica ao frio.

## Regra de segurança da versão

A v0.8.6 não será publicada diretamente para os usuários. O desenvolvimento ocorrerá em branch própria, passará por testes automatizados e por validação prática em servidor central e estações antes de qualquer tag/release oficial.

## Compatibilidade com ensaios já cadastrados

A atualização não pode reinterpretar nem alterar silenciosamente ensaios existentes.

- Registros existentes em `Finalizado` ou `Cancelado` permanecem exatamente como estão.
- Registros existentes em `Aguardando`, `Na Câmara` ou `Em Secagem` continuam no fluxo legado da v0.8.5 por padrão.
- Nenhum ensaio antigo passa a exigir acondicionamento ou frio automaticamente.
- Novos campos e estruturas são opcionais/nulos ou recebem defaults compatíveis.
- O fluxo de frio só é ativado quando estiver explicitamente planejado para o ensaio.
- Ensaios antigos ainda não finalizados poderão optar pelo novo fluxo de frio por ação explícita do usuário, desde que a etapa seja tecnicamente possível naquele ponto.
- Depois que acondicionamento ou frio forem iniciados, a informação não poderá ser removida silenciosamente; mudanças exigirão ação rastreável/justificada.
- Nenhuma nova notificação de frio será criada retroativamente para ensaios antigos que não tenham a etapa de frio ativada.
- Migrações devem ser idempotentes e preservar todo o banco atual.

## Fluxo térmico novo

Para ensaios que tenham resistência térmica ao frio planejada:

1. Resistência térmica ao calor segue o fluxo atual da Tabela 17.
2. Ao finalizar a última etapa do calor, o usuário pode iniciar o acondicionamento:
   - agora; ou
   - informando manualmente a data/hora real.
3. Acondicionamento pós-calor:
   - 20 ± 5 °C;
   - 50 ± 10 % UR;
   - mínimo 24 h;
   - limite 72 h.
4. Depois do mínimo de 24 h, o ensaio de frio pode ser iniciado:
   - agora; ou
   - informando manualmente a data/hora real.
5. Resistência térmica ao frio:
   - campo exibido como `Temperatura mínima ambiente de serviço`;
   - valor padrão quando vazio: -20 °C;
   - faixa de ensaio calculada reduzindo 5 K a 10 K;
   - permanência nominal 24 h;
   - limite 26 h.
6. O frio pode ser marcado como não realizado com justificativa rastreável.

O sistema não deve sugerir nem implementar ensaio de impacto nesse fluxo.

## Notificações do frio

Não enviar e-mail ao iniciar o ensaio de calor.

Quando o frio for realmente iniciado, criar alertas associados à hora real de entrada:

- 1 h antes da retirada nominal de 24 h;
- alerta adicional próximo do limite de 26 h se a retirada ainda não tiver sido registrada;
- alerta crítico ao atingir/ultrapassar o limite;
- cancelar avisos futuros assim que a retirada for registrada.

## Estabilidade e navegação

- Investigar e corrigir tela branca/reinício ao alternar abas.
- Preservar sidebar e moldura principal montadas.
- Trocar somente o conteúdo central.
- Evitar reconstruções/reparenting desnecessários.
- Bloquear navegações concorrentes durante uma transição.
- Adicionar logs específicos de navegação, exceção e reconexão.
- Restaurar animações somente depois que a navegação persistente estiver estável.

## Sincronização entre estações

Alterações feitas em uma estação devem aparecer nas demais sem exigir sair e voltar para a Dashboard. Atualizar de forma leve os dados visíveis de Dashboard, ensaios, agenda, notificações e detalhes.

## Refinamento visual

- Cards de condições, prazos, secagem, acondicionamento e frio em boxes compactos.
- Layout lado a lado quando houver largura suficiente.
- Ícones e hierarquia visual simples, clean e consistente.
- Revisar outras telas com cards excessivamente estendidos.

## Atualizações centralizadas

Preparar arquitetura para o administrador atualizar o servidor e, depois, disparar a atualização das estações pelo servidor central, com status por computador. A ordem servidor -> estações deve ser preservada.

## Assinatura e reputação do instalador

Preparar o pipeline para assinatura Authenticode quando houver certificado de assinatura disponível. O SHA-256 permanece obrigatório.

## Estratégia de validação

Antes de qualquer release oficial:

- lint e formatação;
- testes unitários e de migração;
- testes de regressão com banco da v0.8.5;
- atualização sobre banco já populado;
- ensaios legados em cada situação existente;
- novo fluxo calor -> acondicionamento -> frio;
- notificações do frio;
- navegação rápida/repetitiva entre telas;
- duas ou mais estações simultâneas;
- perda e recuperação de conexão;
- smoke test do instalador como servidor e estação;
- teste real controlado no laboratório.
