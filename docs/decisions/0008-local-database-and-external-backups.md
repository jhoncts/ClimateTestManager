# ADR 0008 — Banco local e backups externos

## Contexto

O banco SQLite permanece aberto durante as operações da janela principal e também pode ser
acessado brevemente pelo notificador. Colocar esse conjunto de arquivos diretamente em uma pasta
sincronizada acrescenta outro processo de leitura e substituição e pode produzir conflitos entre
versões, principalmente no modo WAL ou quando mais de um computador sincroniza o mesmo caminho.

Ao mesmo tempo, manter todas as cópias no mesmo disco não protege o laboratório contra perda,
defeito ou substituição da máquina.

## Decisão

- Solicitar a escolha do armazenamento antes de criar o primeiro administrador.
- Manter o banco ativo em uma pasta local estável, fora do executável.
- Recusar OneDrive, Dropbox, Google Drive, iCloud e caminhos de rede como pasta ativa.
- Criar uma cópia SQLite consistente por dia na pasta local `backups`.
- Quando configurado, criar outra cópia consistente por dia em uma pasta externa, normalmente no
  OneDrive corporativo.
- Manter as 30 cópias diárias mais recentes em cada destino.
- Permitir que somente administradores alterem o destino externo pela interface.
- Preservar `CLIMATETEST_DATA_DIR` como substituição explícita para desenvolvimento e testes.

## Consequências

- O programa não usa o OneDrive como sistema de bloqueio ou compartilhamento de um SQLite vivo.
- A falha do computador não elimina a cópia sincronizada do dia.
- O aplicativo e o notificador resolvem o mesmo caminho por meio de `storage.json`.
- Uma mudança de pasta durante a instalação copia um banco legado com a API de backup e não apaga
  a origem.
- Uma futura operação de restauração continuará exigindo aplicativo e notificador fechados.

## Referências

- [SQLite — SQLite Over a Network, Caveats and Considerations](https://sqlite.org/useovernet.html)
- [Microsoft — Restrições e limitações do OneDrive e SharePoint](https://support.microsoft.com/onedrive/restrictions-and-limitations-in-onedrive-and-sharepoint)
