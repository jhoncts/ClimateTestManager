# Protocolo de validação — ClimateTest Manager v0.5.0

Status inicial: **não executado / não aprovado para uso de produção**

Identificador sugerido: `PV-SC-CTM-005`

Data de emissão: ____/____/________

Laboratório/local: ______________________________________________

## 1. Objetivo e escopo

Demonstrar, com evidência objetiva, que a versão 0.5.0 instalada no ambiente de produção executa
de forma consistente as funções pretendidas de cadastro, cálculo, controle de etapas, registro
de horários, auditoria, usuários, notificações, backup e recuperação. O protocolo valida o
sistema computadorizado; não substitui a validação do método de ensaio ou a calibração dos
equipamentos.

## 2. Equipe e independência

| Função | Nome | Assinatura/data |
|---|---|---|
| Executor dos testes |  |  |
| Revisor técnico independente do desenvolvimento |  |  |
| Responsável pelo sistema/infraestrutura |  |  |
| Aprovador da qualidade |  |  |

O revisor deve comparar resultados críticos com fonte independente, não somente repetir o valor
mostrado pela aplicação.

## 3. Identificação do ambiente (IQ)

| Item | Valor observado | Aceito? |
|---|---|---|
| Executável/pacote | `ClimateTestManager-v0.5.0-windows.zip` | ☐ |
| Hash SHA-256 do pacote |  | ☐ |
| Versão exibida | 0.5.0 | ☐ |
| Regra exibida | `IEC60079-0:2020-T17-v1` | ☐ |
| Esquema exibido | 11 | ☐ |
| Computador/patrimônio |  | ☐ |
| Windows/edição/build |  | ☐ |
| Usuário de serviço/notificador |  | ☐ |
| Pasta local do banco |  | ☐ |
| Pasta externa de backup |  | ☐ |
| Fuso horário e sincronização do relógio |  | ☐ |
| Proteção de disco e controle de acesso |  | ☐ |

Critério: todos os itens identificados; banco fora de pasta sincronizada/rede; backup externo em
destino diferente; relógio correto; somente pacote aprovado instalado.

## 4. Requisitos do usuário e testes de aceitação (OQ/PQ)

Registre `Aprovado`, `Reprovado` ou `N/A` e anexe captura/arquivo/log quando indicado.

| ID | Requisito e desafio | Resultado esperado | Evidência | Resultado |
|---|---|---|---|---|
| URS-01 | Primeiro administrador, senha inválida/válida e login | Regras de senha aplicadas; credencial não reaparece | Capturas sem senha |  |
| URS-02 | Criar Operador, duplicar usuário, desativar e redefinir senha | Ações restritas ao Administrador e auditadas | Tela Usuários/atividade |  |
| URS-03 | Tentar acesso de Operador ao gerenciamento | Acesso indisponível | Captura |  |
| URS-04 | Cadastrar Tamb + ΔT e comparar Ts manualmente | `Ts = Tamb + ΔT` sem divergência | Planilha/cálculo independente |  |
| URS-05 | Testar fronteiras e opções da Tabela 17 | Opção/condição idêntica à fonte controlada | Folha de comparação |  |
| URS-06 | Cadastrar condição personalizada | Referência textual preservada; nenhum Ts inventado | Registro do ensaio |  |
| URS-07 | Iniciar câmara em horário atual e informado | Entrada e ator persistidos; futuro recusado | Atividade |  |
| URS-08 | Calcular retirada nominal e tolerância +30 h | Datas/horas idênticas ao cálculo independente | Folha de comparação |  |
| URS-09 | Prazo em fim de semana | Dia da semana e alerta visíveis | Captura |  |
| URS-10 | Corrigir horário com motivo | Anterior, novo, motivo, data e ator preservados | Atividade |  |
| URS-11 | Tentar sequência cronológica inválida | Operação recusada sem alteração do registro | Captura/atividade |  |
| URS-12 | Pausar/retomar equipamento | Contagem congelada e prazos deslocados corretamente | Folha de comparação |  |
| URS-13 | Cancelar ensaio e tentar excluir iniciado | Motivo exigido; exclusão bloqueada | Atividade |  |
| URS-14 | Exportar CSV com conteúdo iniciado por `=` | Conteúdo neutralizado; dados correspondem à tela | CSV |  |
| URS-15 | Testar e-mail e destinatário recusado | Aceitos/recusados e Message-ID apresentados | Comprovante sem credencial |  |
| URS-16 | Executar notificador duas vezes no mesmo prazo | Cada canal recebe no máximo um aviso por evento | Registros/caixas de teste |  |
| URS-17 | Fechar aplicativo e aguardar tarefa | Aviso é emitido sem janela de terminal | Histórico da tarefa |  |
| URS-18 | Criar backup diário local e externo | Cópias consistentes e fechadas nos dois destinos | Arquivos |  |
| URS-19 | Conferir manifesto de backup | `quick_check=ok`, zero violações e SHA-256 corresponde ao arquivo | Manifesto/cálculo de hash |  |
| URS-20 | Restaurar cópia em pasta isolada | Login, ensaios, atividades e falhas são legíveis | Registro da restauração |  |
| URS-21 | Corromper apenas cópia descartável e repetir backup | Cópia inválida é recusada/recriada; produção intacta | Registro de teste |  |
| URS-22 | Registrar e encerrar falha | Relato/ação imediata preservados; somente Administrador encerra | Tela Configurações |  |
| URS-23 | Recolher/expandir barra lateral | Conteúdo e rolagem permanecem; ícones têm dicas | Capturas |  |
| URS-24 | Redimensionar até largura mínima | Sem sobreposição, corte essencial, flash ou retorno ao topo | Capturas |  |
| URS-25 | Migrar cópia da v0.4.0 | Registros preservados; esquema 11; nenhuma recalculação silenciosa | Comparação antes/depois |  |
| URS-26 | Abrir banco SQLite propositalmente inválido, descartável | Aplicativo bloqueia a abertura e orienta restauração | Captura |  |
| URS-27 | Executar suíte automatizada | Todos os testes, Ruff, formato e diff aprovados | Saída anexada |  |
| URS-28 | Conferir documentos/normas em Configurações e pacote | Base normativa e ressalva de responsabilidade visíveis | Captura/lista de arquivos |  |

O roteiro detalhado de passos está em `docs/MANUAL_TEST_V050.md` e integra este protocolo.

## 5. Validação automatizada

Preencher com a execução feita sobre o código exato do pacote:

```text
Comando Ruff:
Resultado:

Comando de formatação:
Resultado:

Comando Pytest:
Quantidade aprovada:
Cobertura:

Commit/tag:
SHA-256 do ZIP:
```

## 6. Desvios

| Desvio | Teste | Severidade | Impacto em dados/resultados | Correção | Reteste | Situação |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

Nenhum desvio crítico ou alto pode permanecer aberto. Desvio médio/baixo exige justificativa e
aceite formal do risco residual.

## 7. Critérios de aprovação

- Todos os requisitos críticos aprovados.
- Nenhum desvio crítico ou alto aberto.
- Cálculos críticos comparados com fonte independente.
- Migração e restauração demonstradas em cópias isoladas.
- Perfis, trilhas e registro de falha confirmados.
- Pacote e documentação identificados por versão/hash.
- Riscos residuais aceitos e procedimento de operação aprovado.

## 8. Decisão de liberação

☐ Aprovado para uso controlado

☐ Reprovado

☐ Aprovado com restrições descritas abaixo

Restrições/justificativa:

______________________________________________________________________________

______________________________________________________________________________

| Aprovação | Nome | Assinatura | Data |
|---|---|---|---|
| Responsável técnico |  |  |  |
| Qualidade |  |  |  |
| Responsável pelo sistema |  |  |  |
