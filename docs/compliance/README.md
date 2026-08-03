# Dossiê de conformidade do sistema computadorizado

## Declaração correta de escopo

O ClimateTest Manager v0.5.0 foi **projetado para apoiar** os requisitos aplicáveis da
ABNT NBR ISO/IEC 17025:2017 e para executar a condição climática configurada a partir da
Tabela 17 da ABNT NBR IEC 60079-0:2020. Essa declaração não significa certificação do produto,
acreditação automática do laboratório nem dispensa a validação do sistema no ambiente de uso.

A conformidade final é compartilhada entre software, laboratório, infraestrutura e pessoas. O
laboratório precisa aprovar os requisitos, executar a qualificação no Windows de produção,
controlar os documentos, autorizar e treinar usuários, proteger o equipamento, testar a
restauração, avaliar fornecedores, auditar o uso e conservar as evidências pelo prazo definido
em seu sistema de gestão.

## Documentos deste dossiê

| Documento | Finalidade | Situação antes da implantação |
|---|---|---|
| `ISO17025_SOFTWARE_COMPLIANCE_MATRIX.md` | Mapeia cada requisito relevante para controle, evidência e responsabilidade | Revisado tecnicamente; aprovação do laboratório pendente |
| `VALIDATION_PROTOCOL_V050.md` | Define requisitos, testes de aceitação, desvios e assinaturas | Execução no Windows e assinaturas pendentes |
| `DIGITAL_SYSTEM_OPERATION_PROCEDURE.md` | Modelo de procedimento para ciclo de vida, acesso, backup, falhas e mudanças | Deve receber código documental e aprovação interna |
| `RISK_ASSESSMENT_V050.md` | Registra riscos do sistema e controles existentes | Riscos residuais devem ser aceitos pelo laboratório |
| `AUTOMATED_VERIFICATION_V050.md` | Conserva o resultado reproduzível da verificação automatizada desta candidata | Aprovado no ambiente de desenvolvimento; Windows ainda pendente |
| `../MANUAL_TEST_V050.md` | Roteiro operacional detalhado de homologação | Execução final pendente |

## Base normativa e referências consideradas

### Aplicação direta

- ABNT NBR ISO/IEC 17025:2017 — requisitos gerais para a competência de laboratórios de ensaio
  e calibração, especialmente 4.2, 6.2, 6.4, 7.2, 7.5, 7.10, 7.11 e 8.2 a 8.9.
- ABNT NBR IEC 60079-0:2020 — regra técnica de domínio configurada para as condições da
  Tabela 17. A identificação da regra fica registrada com cada ensaio.

### Orientação complementar, não apresentada como certificação

- EUROLAB Technical Report 01/2024, *Guidelines for the Management of Digitalised Systems in
  Laboratories Accredited to ISO/IEC 17025*.
- ISO/IEC 27001:2022 e ISO/IEC 27002:2022 — segurança da informação e controles.
- ISO/IEC/IEEE 12207:2026 — processos de ciclo de vida de software.
- ISO/IEC 25010:2023 — modelo de qualidade de produto.
- ISO 19011:2026 — orientação para auditorias de sistemas de gestão.

Referências públicas de identificação e escopo: [ISO/IEC 17025:2017](https://www.iso.org/standard/66912.html),
[EUROLAB TR 01/2024](https://www.eurolab.org/newsarticles/eurolab-new-technical-report-published%21/),
[ISO/IEC 27001:2022](https://www.iso.org/standard/27001),
[ISO/IEC 27002:2022](https://www.iso.org/standard/75652.html),
[ISO/IEC/IEEE 12207:2026](https://www.iso.org/standard/90219.html),
[ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html) e
[ISO 19011:2026](https://www.iso.org/standard/19011.html).

## Identificação técnica da versão

- Software: ClimateTest Manager v0.5.0.
- Esquema do banco: 11.
- Regra climática: `IEC60079-0:2020-T17-v1`.
- Banco ativo: SQLite local com chaves estrangeiras, WAL e verificação de integridade na abertura.
- Backup: cópia consistente pela API SQLite, verificação `quick_check`, conferência de chaves
  estrangeiras e manifesto SHA-256 ao lado de cada cópia automática.
- Evidência automatizada: suíte Pytest, Ruff e verificação de formatação.

## Regra de liberação

O sistema somente deve passar de “candidato” para “aprovado para uso” quando o protocolo de
validação estiver concluído, todos os desvios críticos ou altos estiverem resolvidos, uma
restauração tiver sido demonstrada e as assinaturas de execução, revisão técnica e aprovação da
qualidade estiverem preenchidas.
