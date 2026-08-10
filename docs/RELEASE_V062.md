# ClimateTest Manager v0.6.2

Correção do servidor Windows empacotado sem console.

O executável `ClimateTestServer.exe` agora garante streams padrão válidos antes de iniciar o Flet/Uvicorn. Isso evita a falha `Unable to configure formatter 'default'` / `AttributeError: 'NoneType' object has no attribute 'isatty'` observada quando o servidor é iniciado pelo instalador ou pelo Agendador de Tarefas em modo sem console.

A v0.6.2 mantém as correções de instalação resiliente e preservação de dados introduzidas na v0.6.1.
