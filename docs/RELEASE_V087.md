# ClimateTest Manager v0.8.7 — R12

Versão de transição para atualização controlada por um técnico e apresentação pública como projeto
pessoal independente.

## Atualizações

- Somente o servidor central monitora novas Releases no GitHub.
- Estações deixam de consultar o canal público e não exibem alertas de atualização.
- O aviso do servidor explica que o servidor deve ser atualizado primeiro.
- Novo distribuidor remoto copia, verifica, instala e testa a versão em cada estação.
- Novo bootstrap habilita WinRM uma única vez e restringe o firewall ao servidor informado.
- Relatório CSV identifica estações atualizadas, prontas ou com falha.
- Releases sem Authenticode são permitidas para o estágio de portfólio, sempre identificadas e
  protegidas por SHA-256; o suporte a assinatura permanece pronto para o futuro.

## Autoria e independência

- Projeto pessoal criado e mantido por Jhon Cleiton.
- Nenhuma organização de teste é citada ou apresentada como proprietária, parceira ou apoiadora.
- `NOTICE.md` descreve a independência do projeto.
- `LICENSE` preserva todos os direitos do autor e permite visualização para avaliação do portfólio.

## Ordem da primeira implantação

1. Fazer backup externo e verificado do banco do servidor central.
2. Instalar v0.8.7 / R12-20260825 no servidor central.
3. Executar uma vez `enable_remote_update_station.ps1` em cada estação existente.
4. Preencher `C:\ProgramData\ClimateTestManager\stations.txt` no servidor.
5. Distribuir v0.8.7 às estações pelo atalho administrativo do servidor.
6. Nas próximas versões, repetir apenas o fluxo do servidor e do atalho de distribuição.
