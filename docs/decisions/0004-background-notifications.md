# ADR 0004 — Notificações locais em segundo plano

## Contexto

Os prazos precisam ser avisados mesmo quando a janela principal estiver fechada. Um processo
mantido continuamente na bandeja aumenta a complexidade, pode ser encerrado sem percepção e ainda
não resolve o cenário de reinicialização do Windows.

## Decisão

Usar uma tarefa agendada do Windows, executada a cada 5 minutos, para chamar diretamente
`ClimateTestNotifier.exe` ou, no ambiente de desenvolvimento, `pythonw.exe`. A ação periódica não
passa por `powershell.exe` ou `cmd.exe`, evitando a janela que aparecia a cada execução. Os avisos
pendentes e entregues ficam registrados no SQLite.

O aplicativo nunca instalará a tarefa silenciosamente: a ativação e a remoção dependem de ações
explícitas na tela de Configurações.

## Consequências

- A janela principal pode ficar fechada.
- O computador e a sessão do Windows precisam estar ativos.
- Avisos não são duplicados após reinicializações.
- A tela de Configurações mostra o banco monitorado, a última verificação e permite testar uma
  notificação antes de ativar a tarefa.
- A entrega em computador desligado dependerá de um canal externo futuro.
- Calendário e e-mail automáticos serão implementados com login e OAuth, sem senha persistida.
