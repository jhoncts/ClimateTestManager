# ClimateTest Manager v0.6.3

Correção de atualização do servidor central no Windows.

- encerra e desabilita temporariamente as tarefas da versão anterior antes de substituir executáveis;
- encerra `ClimateTestServer.exe`, `ClimateTestNotifier.exe` e o cliente antes da cópia dos novos arquivos;
- impede a instalação de continuar silenciosamente se algum processo antigo não puder ser encerrado;
- mantém os dados e backups em `C:\ProgramData\ClimateTestManager`;
- adiciona teste automatizado de atualização com `ClimateTestServer.exe` propositalmente em execução durante o instalador.
