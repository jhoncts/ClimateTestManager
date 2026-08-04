# Modelo de procedimento — gestão do ClimateTest Manager

Código sugerido: `POP-SC-CTM-001`

Revisão: 00

Situação: modelo a ser adaptado, codificado e aprovado pelo laboratório

## 1. Finalidade

Controlar o ciclo de vida do ClimateTest Manager, incluindo responsável, instalação, acesso,
uso, backup, falhas, mudanças, validação, auditoria e retirada de serviço.

## 2. Responsabilidades mínimas

- **Responsável técnico:** aprova regra/método, impacto em resultados e retomada após falha.
- **Qualidade:** aprova validação, documentos, desvios, ações corretivas e auditorias.
- **Administrador do sistema:** instala pacote aprovado, gerencia usuários, backup, incidentes e
  evidências técnicas; não pode aprovar sozinho sua própria validação.
- **Operador autorizado:** usa somente funções treinadas, confere dados e relata falhas.
- **TI:** protege Windows, disco, relógio, energia, malware, permissões e provedores externos.

## 3. Inventário e identificação

Registrar versão do software, regra, esquema, hash do pacote, computador, Windows, local do banco,
destinos de backup, proprietário, data de entrada em serviço, validação e histórico de mudanças.

## 4. Instalação e aceitação

1. Obter o pacote de fonte aprovada e conferir SHA-256.
2. Instalar em computador qualificado e com relógio sincronizado.
3. Manter o banco ativo em disco local; nunca em OneDrive, outro sincronizador ou rede.
4. Escolher destino externo de backup com acesso restrito.
5. Executar `VALIDATION_PROTOCOL_V050.md` usando dados fictícios e pasta isolada.
6. Liberar uso somente após aprovação formal e arquivamento da evidência.

## 5. Acesso

1. Criar conta nominal para cada pessoa; contas compartilhadas são proibidas.
2. Conceder Administrador somente a pessoal autorizado.
3. Relacionar cada perfil às funções autorizadas na matriz de competência.
4. Desativar imediatamente usuários desligados ou que perderam autorização.
5. Revisar usuários ativos e administradores na periodicidade definida pelo laboratório.
6. Proteger a sessão Windows, a pasta de dados e os backups; usar criptografia de disco quando
   requerida pela avaliação de risco.

## 6. Operação e conferência

1. Conferir cliente, processo, produto, quantidade, origem da condição e referência antes de
   salvar.
2. Conferir o resumo calculado e o dia da semana dos prazos antes de iniciar a câmara.
3. Usar “Registrar agora” somente para operação em tempo real; usar registro posterior para fato
   já ocorrido.
4. Nunca ajustar o relógio para alterar um registro. Corrigir horário pelo fluxo auditável e
   informar o motivo.
5. Investigar discrepâncias antes de avançar. Não editar diretamente o SQLite.

## 7. Backup, verificação e restauração

1. Manter um backup diário local e outro em destino externo.
2. Conferir periodicamente a existência do `.db` e do respectivo `.manifest.json`.
3. Verificar que o manifesto informa `quick_check: ok`, zero violações e SHA-256 correspondente.
4. Aplicar estratégia organizacional compatível com 3-2-1 quando o risco exigir: três cópias, em
   dois meios, uma fora do equipamento/local.
5. Executar restauração trimestral ou na periodicidade aprovada, sempre em pasta isolada.
6. Registrar arquivo usado, hash, data, executor, tempo de recuperação e conferência de usuários,
   ensaios, atividades e falhas.
7. Em perda do computador, instalar o pacote aprovado em equipamento qualificado, copiar uma
   cópia verificada para pasta local e repetir testes críticos antes da retomada.

## 8. Falhas, trabalho não conforme e ações corretivas

1. Ao detectar falha, interromper a função afetada e preservar evidências.
2. Abrir **Configurações → Falhas do sistema → Registrar falha**.
3. Informar impacto, descrição e ação imediata sem dados vagos.
4. Avaliar ensaios/resultados potencialmente afetados e aplicar o procedimento de trabalho não
   conforme do laboratório.
5. Corrigir somente após análise de causa e autorização.
6. O Administrador registra ação corretiva e verificação de eficácia; o relato original permanece.
7. Retomar somente com autorização técnica quando houver impacto em resultados.

## 9. Mudanças e atualização

1. Abrir solicitação de mudança com motivo, risco, componentes afetados e plano de reversão.
2. Revisar requisitos e matriz de conformidade.
3. Executar testes automatizados e regressão proporcional ao risco.
4. Testar migração sobre cópia; nunca usar primeiro o banco real.
5. Obter aprovação independente antes da instalação.
6. Fazer backup verificado, instalar pacote por hash, executar testes pós-instalação e registrar a
   nova versão.
7. Manter a versão anterior e procedimento de reversão até confirmar estabilidade.

Mudanças de Windows, biblioteca, banco, regra normativa, infraestrutura, sincronizador, SMTP ou
política de segurança também precisam de avaliação de impacto.

## 10. Documentos, registros e retenção

Controlar manual, matriz, protocolo executado, riscos, inventário, releases, hashes, treinamentos,
usuários, auditorias, incidentes e restaurações conforme o procedimento documental do laboratório.
O prazo de retenção deve atender contrato, norma, acreditador e política interna. A retenção de 30
backups é uma rotação técnica e não define o prazo dos registros de ensaio, que permanecem no
banco até descarte formal autorizado.

## 11. Auditoria periódica

Incluir no programa de auditoria: usuários e competências; amostra de alterações; falhas abertas;
manifests e restauração; versão/hash; tarefa do notificador; proteção do computador; documentos
vigentes; mudanças desde a última auditoria; e ações corretivas.

## 12. Retirada de serviço

1. Autorizar formalmente a retirada.
2. Criar e verificar cópia final; registrar hash, formato e prazo de retenção.
3. Demonstrar que os dados continuam legíveis durante a retenção.
4. Revogar acessos, tarefa e credenciais SMTP.
5. Desinstalar o aplicativo somente após confirmar o arquivo.
6. Descartar dados e mídias de modo autorizado, confidencial e registrado ao fim da retenção.
