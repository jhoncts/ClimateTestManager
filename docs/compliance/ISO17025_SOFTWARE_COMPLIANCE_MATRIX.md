# Matriz de conformidade — software e ABNT NBR ISO/IEC 17025:2017

Data da análise: 03/08/2026

Produto analisado: ClimateTest Manager v0.5.0

Regra de domínio: `IEC60079-0:2020-T17-v1`

## Legenda

- **Software**: controle implementado e testável no produto.
- **Compartilhado**: o produto fornece controle ou evidência, mas o laboratório precisa completar
  o atendimento por procedimento, infraestrutura, autorização ou revisão.
- **Laboratório**: requisito organizacional fora do escopo do aplicativo.
- **Não aplicável ao aplicativo**: o requisito pode existir no laboratório, mas não é executado
  por este software.

Esta matriz avalia capacidade funcional; ela não declara acreditação. A coluna “ação antes do
uso” é parte da conclusão normativa e não pode ser ignorada numa auditoria.

## 4 — Requisitos gerais

| Item | Aplicação ao sistema | Controle/evidência | Responsabilidade | Ação antes do uso |
|---|---|---|---|---|
| 4.1 Imparcialidade | O sistema não toma decisão de conformidade nem altera critérios por cliente | Regra versionada, campos técnicos persistidos e trilha das alterações | Compartilhado | Laboratório deve identificar riscos à imparcialidade, controlar conflitos e revisar decisões humanas |
| 4.2 Confidencialidade | Dados de clientes, usuários e ensaios são confidenciais | Login local, perfis, sessão revogável, senha com PBKDF2, SMTP protegido pelo Windows, banco local e exportação sob ação do usuário | Compartilhado | Restringir pasta/Windows, usar criptografia de disco, controlar backups/exportações, definir retenção e confidencialidade de pessoal e fornecedores |

## 5 — Requisitos de estrutura

| Item | Aplicação ao sistema | Controle/evidência | Responsabilidade | Ação antes do uso |
|---|---|---|---|---|
| 5.1 a 5.7 Estrutura, responsabilidade e autoridade | O aplicativo identifica usuários, mas não constitui a organização legal nem define toda a autoridade técnica | Perfis Administrador/Operador e ator real nas atividades | Laboratório | Documentar entidade, organograma, responsabilidades, substituições e autoridade para interromper trabalho |

## 6 — Requisitos de recursos

| Item | Aplicação ao sistema | Controle/evidência | Responsabilidade | Ação antes do uso |
|---|---|---|---|---|
| 6.2 Pessoal | Somente contas cadastradas operam o sistema; administração de contas é restrita | Usuários ativos, perfis, trilha de segurança e ausência de autocadastro | Compartilhado | Definir matriz de competência/autorização por função, treinar, avaliar competência e remover acesso ao desligar pessoas |
| 6.3 Instalações e ambiente | Windows, relógio, energia e conectividade influenciam prazos e notificações | Avisos explicam dependência do computador e da sessão; banco ativo local | Compartilhado | Proteger estação, sincronizar relógio, assegurar energia/UPS quando necessário, controlar acesso físico e monitorar ambiente de TI |
| 6.4.1 Equipamentos, inclusive software e dados | O ClimateTest Manager é equipamento de apoio ao ensaio | Identificação da versão, regra, esquema e pacote controlado | Compartilhado | Incluir o software no inventário de equipamentos/sistemas e atribuir responsável |
| 6.4.2 a 6.4.4 Acesso, especificação e verificação antes do serviço | Acesso é autenticado e o protocolo define aceitação | Login/perfis; testes automatizados; protocolo de validação v0.5.0 | Compartilhado | Executar e aprovar IQ/OQ/PQ antes do uso real; registrar computador, Windows, executáveis e resultados |
| 6.4.5 a 6.4.8 Adequação, exatidão, calibração e identificação | O software calcula prazos; não mede temperatura/umidade nem calibra câmaras | Cálculos determinísticos e testes de limites; regra versionada | Compartilhado | Demonstrar casos de cálculo contra fonte independente; manter calibração e identificação das câmaras fora do sistema |
| 6.4.9 Equipamento fora de serviço | Falha pode comprometer registros ou prazos | Tela “Falhas do sistema”, ação imediata, impacto e ação corretiva; pausa de equipamentos | Compartilhado | Procedimento deve interromper uso, avaliar trabalho afetado e aplicar 7.10 quando necessário |
| 6.4.10 Verificações intermediárias | Aplicável a verificações periódicas do software e restauração | Testes automatizados; manifesto de backup | Compartilhado | Definir periodicidade, executar casos críticos e restauração, registrar resultados |
| 6.4.11 Fatores de correção | Não há fatores de correção de equipamentos aplicados pelo aplicativo | Não aplicável à versão | Não aplicável ao aplicativo | Controlar fatores nos métodos/equipamentos correspondentes |
| 6.4.12 Ajustes não intencionais | Alterações técnicas exigem motivo e ficam auditadas; regra não é editável na interface | Trilha anterior/novo/motivo/ator/data | Compartilhado | Restringir arquivos e instalação pelo Windows; distribuir apenas pacote aprovado |
| 6.4.13 Registros do equipamento | Versão, regra, falhas e validação compõem o histórico do sistema | Configurações, dossiê, Git/release, registro de falhas | Compartilhado | Manter inventário, localização, responsável, histórico de versões/manutenções e decisão de retirada |
| 6.5 Rastreabilidade metrológica | O software não gera rastreabilidade de instrumentos | Não aplicável | Laboratório | Manter certificados e cadeia metrológica das câmaras/instrumentos |
| 6.6 Produtos e serviços externos | OneDrive, SMTP, Windows e componentes de software podem ser provedores externos | Configuração explícita; falhas de SMTP/backup são detectáveis | Compartilhado | Avaliar/aprovar provedores, termos, disponibilidade, confidencialidade, atualizações e suporte |

## 7 — Requisitos de processo

| Item | Aplicação ao sistema | Controle/evidência | Responsabilidade | Ação antes do uso |
|---|---|---|---|---|
| 7.1 Análise de pedidos, propostas e contratos | Campos de cliente/processo identificam o trabalho, mas o sistema não executa análise contratual | Identificação persistida no ensaio | Laboratório | Conservar análise de capacidade, método, recursos e acordo com cliente em processo controlado |
| 7.2.1 Seleção, verificação e validação de métodos | O aplicativo aplica uma versão explícita da Tabela 17 | Snapshot imutável da condição, regra versionada, testes de opção/limites | Compartilhado | Confirmar edição aplicável, verificar método antes do uso, controlar cópia legal da norma e aprovar alterações |
| 7.2.2 Validação de métodos | O software não valida método de ensaio não normalizado | Casos de software não equivalem à validação do método laboratorial | Laboratório | Validar métodos quando aplicável e conservar características de desempenho |
| 7.3 Amostragem | Não existe módulo de plano/registro de amostragem | Não aplicável à função atual | Não aplicável ao aplicativo | Usar procedimento e registros externos se o laboratório realizar amostragem |
| 7.4 Manuseio de itens | Quantidade, produto e etapa são registrados; não há cadeia de custódia completa | Identificação do processo/produto/amostras e situação | Compartilhado | Controlar recebimento, identificação física, armazenamento, desvios e descarte por procedimento próprio |
| 7.5.1 Registros técnicos | O sistema conserva entradas, resultados calculados, horários, pessoas e fatores que afetam o prazo | Snapshot da condição, horários, pausas, notas e eventos técnicos | Compartilhado | Definir quais registros externos completam o ensaio e revisar sua suficiência para repetição |
| 7.5.2 Alterações em registros | Correções preservam anterior/novo, motivo, data e responsável; exclusão é limitada a rascunho não iniciado | `audit_events`, confirmações e autenticação | Software | Proibir edição direta do SQLite e auditar amostras de eventos periodicamente |
| 7.6 Incerteza de medição | O software não estima incerteza | Não aplicável à função atual | Laboratório | Avaliar incerteza do ensaio conforme método e política aplicável |
| 7.7 Garantia da validade dos resultados | Testes e conferências apoiam validade dos cálculos, mas não substituem controles técnicos do laboratório | Pytest, protocolo de validação, indicadores e histórico | Compartilhado | Planejar controles de validade, analisar tendências e agir sobre resultados insatisfatórios |
| 7.8 Relato de resultados | CSV é exportação operacional, não relatório/laudo ISO 17025 controlado | Neutralização de fórmulas e identificação dos dados exportados | Compartilhado | Usar sistema aprovado de emissão/revisão de relatório ou controlar modelo externo; não tratar o CSV como laudo |
| 7.9 Reclamações | Não há módulo de reclamações | Não aplicável à função atual | Laboratório | Manter processo de recebimento, investigação e resposta fora do aplicativo |
| 7.10 Trabalho não conforme | Falhas, pausas e cancelamentos podem indicar trabalho afetado | Registro de falhas, motivos, ação imediata, ação corretiva e trilha técnica | Compartilhado | Avaliar impacto/aceitabilidade, decidir retomada, notificar cliente quando necessário e vincular ao processo interno de não conformidade |
| 7.11.1 Acesso a dados e informações | Usuários autenticados acessam dados necessários ao fluxo | Banco local único, telas de consulta, exportação e backups | Compartilhado | Definir disponibilidade, responsáveis e contingência quando o computador estiver indisponível |
| 7.11.2 Validação do sistema e mudanças | Funções possuem testes e versão, mas a validação formal depende do ambiente real | Suíte automatizada, protocolo, changelog, regra/esquema versionados | Compartilhado | Aprovar requisitos, executar protocolo no Windows; toda atualização deve ter análise de impacto, teste e autorização antes da instalação |
| 7.11.3(a) Proteção contra acesso não autorizado | Login, perfis, sessões revogáveis e administração restrita | `users`, `user_sessions`, `security_audit_events` | Compartilhado | Proteger Windows/pasta, aplicar bloqueio de tela, princípio de menor privilégio e criptografia de disco |
| 7.11.3(b) Proteção contra adulteração e perda | Alterações operacionais são auditadas e backups são consistentes | Trilha anterior/novo; backup SQLite; manifesto SHA-256 | Compartilhado | Restringir acesso direto ao arquivo, controlar exportações, usar proteção antimalware e testar restauração |
| 7.11.3(c) Ambiente conforme especificações | Banco ativo é bloqueado em sincronizadores e rede; pacote é para Windows 11 | Assistente de armazenamento e validações de caminho | Compartilhado | Qualificar computador, Windows, espaço, data/hora, energia e política de atualização |
| 7.11.3(d) Integridade de dados e informações | Transações, chaves estrangeiras, WAL, validação cronológica e checagem ao abrir | SQLAlchemy/SQLite, `PRAGMA foreign_keys`, `quick_check`, testes | Software | Conservar evidência da validação e investigar qualquer bloqueio de integridade |
| 7.11.3(e) Falhas e ações | Falhas podem ser abertas por qualquer usuário e encerradas por administrador | `system_incidents`, ação imediata e corretiva sem substituir relato original | Compartilhado | Avaliar resultados afetados, registrar causa, eficácia e vínculo com ação corretiva do SGQ |
| 7.11.4 Sistema externo | SMTP e OneDrive são externos; o sistema principal é desenvolvido internamente | Configuração, diagnóstico de entrega e backup externo fechado | Compartilhado | Definir requisitos contratuais e confirmar que provedores atendem segurança/disponibilidade necessárias |
| 7.11.5 Instruções e dados de referência disponíveis | Manual, procedimento, matriz, ajuda contextual e regra identificada | Pacote inclui `documentacao-conformidade` | Compartilhado | Disponibilizar versões aprovadas no ponto de uso e remover cópias obsoletas |
| 7.11.6 Cálculos e transferências verificados | Cálculos de condição/prazo, CSV e migração possuem testes automatizados | Testes unitários e protocolo com casos independentes | Compartilhado | Conferir casos críticos com fonte independente e revisar importações/migrações após atualização |

## 8 — Requisitos do sistema de gestão

| Item | Aplicação ao sistema | Controle/evidência | Responsabilidade | Ação antes do uso |
|---|---|---|---|---|
| 8.1 Opções do sistema de gestão | O software é uma ferramenta dentro do SGQ, não o SGQ completo | Dossiê de conformidade | Laboratório | Definir opção A/B e integrar os documentos ao SGQ acreditado |
| 8.2 Documentação do sistema | Há manual, arquitetura, regras, procedimento e matriz | Pasta `docs` e pacote controlado | Compartilhado | Atribuir códigos, revisores, aprovadores, vigência e distribuição interna |
| 8.3 Controle de documentos | Versões ficam no repositório/release, mas a aprovação documental é externa | Git, changelog, pacote versionado | Compartilhado | Aprovar antes da emissão, identificar revisão, bloquear documentos obsoletos e controlar externos |
| 8.4 Controle de registros | Registros são identificáveis, pesquisáveis e copiados; não há exclusão automática dos ensaios | SQLite, trilhas, 30 backups por destino e manifestos | Compartilhado | Definir retenção, acesso, arquivo, recuperação e descarte; proteger backups e executar restauração periódica |
| 8.5 Riscos e oportunidades | Avaliação inicial acompanha o dossiê | `RISK_ASSESSMENT_V050.md` | Compartilhado | Revisar riscos após incidentes, atualizações, mudança de infraestrutura ou de norma |
| 8.6 Melhoria | Changelog, testes e falhas geram entradas para melhoria | Histórico de versão e incidentes | Compartilhado | Analisar feedback, indicadores e oportunidades no SGQ |
| 8.7 Ações corretivas | Incidentes conservam ação imediata e corretiva, mas análise de causa/eficácia é responsabilidade do SGQ | Registro de falhas e encerramento administrativo | Compartilhado | Aplicar metodologia do laboratório, avaliar causa/recorrência/eficácia e atualizar riscos |
| 8.8 Auditorias internas | O sistema fornece trilhas e evidências consultáveis | Atividades, segurança, falhas, backups e dossiê | Compartilhado | Incluir sistema no programa de auditoria; selecionar amostras, registrar constatações e acompanhar ações |
| 8.9 Análise crítica pela direção | O software pode fornecer evidências, mas não realiza a análise | Exportações, indicadores e histórico | Laboratório | Incluir desempenho, falhas, riscos, recursos, auditorias e eficácia das ações na análise crítica |

## Conclusão da análise

O produto cobre os controles técnicos que lhe cabem: autenticação, autoria, trilha de alterações,
regra versionada, validações de fluxo, consistência transacional, verificação do banco, backups
com evidência, notificações idempotentes e registro de falhas/ações corretivas. Os pontos que
continuam **pendentes antes da liberação** são deliberadamente externos ao código: execução e
aprovação do protocolo no Windows real, qualificação da infraestrutura, matriz de autorização e
competência, procedimento documental aprovado, exercício de restauração, avaliação dos
provedores, definição de retenção e inclusão do sistema nas auditorias internas.
