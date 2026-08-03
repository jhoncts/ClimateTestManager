# Avaliação de riscos — ClimateTest Manager v0.5.0

Data-base: 03/08/2026

Método: probabilidade (P) e impacto (I) de 1 a 5; nível = P × I.

Faixas sugeridas: 1–4 baixo, 5–9 médio, 10–15 alto, 16–25 crítico.

Os valores residuais são proposta técnica. O laboratório deve revisar e aceitar cada risco no
ambiente real.

| ID | Risco/causa | Efeito | Inicial | Controles existentes | Residual | Responsável/ação pendente |
|---|---|---|---:|---|---:|---|
| R-01 | Acesso por pessoa não autorizada | Exposição ou alteração de registros | 15 | Login nominal, senha forte, sessões revogáveis, perfis e trilha de segurança | 6 | TI/Qualidade: pasta restrita, bloqueio de tela, revisão de acessos e criptografia de disco |
| R-02 | Conta compartilhada | Autoria incorreta | 12 | Usuários nominais e ator em cada ação | 4 | Gestor: proibir compartilhamento e auditar contas |
| R-03 | Edição direta do SQLite | Adulteração fora da trilha | 20 | Banco local não exposto pela interface, chaves estrangeiras e verificação ao abrir | 8 | TI: negar acesso à pasta e monitorar cópias/exportações |
| R-04 | Falha de SSD/computador | Perda de registros | 20 | Backup diário local e externo fechado, 30 cópias por destino, manifesto | 6 | Administrador: confirmar destino externo e testar restauração periodicamente |
| R-05 | Banco ativo no OneDrive/rede | Corrupção/conflito de sincronização | 20 | Configuração bloqueia sincronizadores e caminhos de rede | 4 | Administrador: não contornar o bloqueio |
| R-06 | Backup existente, mas ilegível | Falsa sensação de recuperação | 16 | `quick_check`, chaves estrangeiras, SHA-256 e manifesto; cópia corrompida é recriada | 6 | Qualidade: exercício documentado de restauração |
| R-07 | Relógio/fuso incorreto | Prazos e autoria temporal incorretos | 16 | Horários visíveis, validação cronológica e correção auditável | 8 | TI: sincronização de hora; operador confere antes do início |
| R-08 | Regra normativa errada/obsoleta | Condição de ensaio incorreta | 20 | Regra identificada e snapshot imutável por ensaio | 8 | Responsável técnico: controlar norma, avaliar revisão e revalidar antes de atualizar |
| R-09 | Erro de cálculo/regressão | Retirada ou limite incorreto | 20 | Funções determinísticas, testes de limites, protocolo com fonte independente | 5 | Revisor independente: aprovar OQ/PQ e repetir após mudança |
| R-10 | Registro posterior tratado como tempo real | Evidência temporal enganosa | 12 | Opções visualmente separadas, confirmação e horário persistido | 4 | Treinamento e auditoria por amostragem |
| R-11 | Operação futura ou ordem impossível | Cronologia inválida | 16 | Datas futuras e sequências inconsistentes são recusadas | 4 | Manter testes de regressão |
| R-12 | Correção sem justificativa | Perda de rastreabilidade | 15 | Motivo obrigatório, anterior/novo/ator/data | 3 | Auditoria amostral dos eventos |
| R-13 | Exclusão indevida | Perda de registro técnico | 15 | Exclusão somente antes do início; cancelamento justificado para ativos | 4 | Restringir acesso direto ao banco e definir retenção |
| R-14 | Notificação não entregue | Retirada atrasada | 15 | Agenda interna, tarefa a cada 5 min, e-mail/Windows independentes e diagnóstico | 8 | Operação: Agenda é referência; monitorar última execução e não depender só de e-mail |
| R-15 | Notificação duplicada | Confusão operacional | 9 | Chave única por evento e controle por canal | 3 | Testar após atualização do notificador |
| R-16 | Queda de energia | Indisponibilidade ou transação interrompida | 15 | Transações SQLite, WAL e recuperação do banco | 8 | TI: avaliar UPS e contingência manual |
| R-17 | Malware/roubo do computador | Perda/confidencialidade | 20 | Backup externo e autenticação do aplicativo | 10 | TI: antimalware, atualização, criptografia e controle físico |
| R-18 | Atualização sem validação | Função incompatível ou dado migrado incorretamente | 20 | Esquema/release versionados, migração testada e changelog | 8 | Mudança formal, cópia, protocolo e aprovação antes de instalar |
| R-19 | Dependência de SMTP/OneDrive | Aviso/backup indisponível ou exposição | 12 | Erros detectáveis e banco principal local | 6 | Avaliar provedores, políticas, conta dedicada e contingência |
| R-20 | CSV interpretado como laudo | Relato incompleto ao cliente | 12 | CSV chamado de exportação operacional | 6 | Procedimento deve proibir uso como relatório ISO 17025 não aprovado |
| R-21 | Falha não registrada/tratada | Recorrência e impacto desconhecido | 16 | Tela de falhas com contenção e ação corretiva | 6 | Treinar todos para relatar; Qualidade revisar abertos e eficácia |
| R-22 | Administrador único indisponível | Perda de capacidade administrativa | 12 | Proteção contra remover o último administrador; vários admins permitidos | 6 | Manter ao menos dois administradores autorizados; transferência principal fica para versão futura |
| R-23 | Documento/versão errada no ponto de uso | Operação com instrução obsoleta | 12 | Pacote contém documentação versionada e tela identifica base normativa | 5 | Controle documental interno e remoção de cópias obsoletas |
| R-24 | Falha de restauração por mudança tecnológica | Registros ilegíveis na retenção | 15 | SQLite aberto e exportação CSV | 8 | Testar legibilidade ao longo da retenção e planejar migração/arquivo |

## Critérios de reavaliação

Reavaliar este documento após falha crítica/alta, mudança de versão ou norma, alteração do Windows
ou computador, novo provedor, mudança de destino de dados, constatação de auditoria, restauração
malsucedida ou mudança relevante do processo laboratorial.
