# Validação manual da v0.5.0 no Windows

Este roteiro valida a migração da v0.4.0, o primeiro acesso, os usuários e o pacote final sem usar
o banco real do laboratório.

## 1. Preparar o primeiro acesso e o armazenamento isolado

No PowerShell, com a branch `feat/v0.5.0-auth-onboarding` aberta:

```powershell
$validationRoot = "C:\Scripts\ClimateTestManager\validacao-v0.5.0-" +
    (Get-Date -Format "yyyyMMdd-HHmm")
New-Item -ItemType Directory -Path $validationRoot -Force | Out-Null

Remove-Item Env:\CLIMATETEST_DATA_DIR -ErrorAction SilentlyContinue
$env:CLIMATETEST_STORAGE_CONFIG = "$validationRoot\storage.json"
Remove-Item Env:\CLIMATETEST_TEST_CONTROLS -ErrorAction SilentlyContinue
flet run src/main.py
```

Na tela **Onde os dados serão protegidos?**:

1. Escolha `$validationRoot\dados` para o banco local.
2. Escolha uma pasta de teste no OneDrive ou `$validationRoot\OneDrive-simulado` para os backups.
3. Marque a confirmação e continue.
4. Tente antes escolher uma pasta com `OneDrive` para o banco ativo e confirme que o sistema
   recusa essa combinação.

Não use a pasta do banco real durante esta validação. A variável `CLIMATETEST_DATA_DIR` ignora o
assistente e deve ser usada somente nas demais rodadas automatizadas ou isoladas.

## 2. Primeiro administrador

1. Depois de salvar os locais, confirme que aparece **Configuração do primeiro acesso**.
2. Tente confirmar com uma senha curta e confira a mensagem de validação.
3. Cadastre nome, sobrenome, usuário, e-mail e uma senha com oito ou mais caracteres, letra e
   número.
4. Confirme que o aplicativo abre o guia orientado a tarefas.
5. Confira os tópicos e clique em **Começar a usar**.
6. Confirme que o nome e o perfil `Administrador` aparecem na barra lateral.

Resultado esperado: a senha nunca aparece no histórico ou nas telas depois do cadastro.
Os campos devem permanecer dentro do cartão, inclusive com a janela na largura mínima.

## 3. Usuários e perfis

1. Abra **Usuários** e cadastre uma conta com perfil `Operador`.
2. Tente cadastrar novamente o mesmo usuário usando letras maiúsculas.
3. Confirme que a duplicidade é recusada.
4. Corrija nome, e-mail ou usuário da conta.
5. Redefina a senha do operador.
6. Clique para sair da conta, confirme que o diálogo permite permanecer conectado e somente
   depois confirme a saída.
7. Entre com o operador e a nova senha.
8. Confirme que **Usuários** não aparece para o operador.
9. Abra **Guia de uso** e confirme que os tópicos podem ser consultados novamente.
10. No administrador, abra **Configurações**, escolha uma foto e confira o avatar na barra
    lateral.
11. Remova a foto, confirme a ação no diálogo e verifique que as iniciais voltam a aparecer.

Resultado esperado: os diálogos usam cabeçalho, orientação e ação principal consistentes. Os
campos ficam em grade compacta quando houver espaço e são empilhados sem ultrapassar a janela.

## 4. Sessão persistente

1. Na tela de login, marque **Manter conectado neste computador por 30 dias**.
2. Entre e feche a aplicação normalmente.
3. Abra novamente.
4. Confirme que o Dashboard abre sem solicitar a senha.
5. Use **Sair da conta** na barra lateral.
6. Confirme que a sessão permanece aberta ao escolher **Permanecer conectado**.
7. Repita a ação, escolha **Sim, sair da conta**, abra o aplicativo outra vez e confirme que o
   login voltou a ser exigido.

## 5. Auditoria com usuário real

1. Entre com uma conta conhecida.
2. Cadastre um ensaio de demonstração.
3. Abra os detalhes e confira o primeiro evento.
4. Inicie a câmara, corrija os dados e faça uma pausa com motivo.
5. Abra **Atividades**.

Resultado esperado: cada nova ação mostra `Nome Sobrenome (@usuario)`. Registros antigos da
v0.4.0 podem continuar como `Não identificado`.

## 6. Horários operacionais

Na tela de detalhes, confirme que as ações estão separadas:

1. **Registrar com o horário atual** para uma operação feita naquele momento.
2. **Informar outro horário** para um registro posterior.
3. Antes de confirmar a entrada da câmara, confira se aparecem entrada, retirada nominal e limite
   com tolerância em três cartões grandes, cada um com dia da semana, data e horário.
4. Escolha um horário cuja retirada nominal caia no sábado ou domingo e confirme a etiqueta
   **FIM DE SEMANA** e o alerta para conferir a disponibilidade da equipe.

Valide entrada da câmara, retirada, início da secagem e finalização. Cada troca de etapa deve
mostrar o horário e aguardar confirmação. Datas futuras devem ser
recusadas. A retirada antes do prazo nominal também deve ser recusada.

Depois, valide a correção independente dos quatro horários:

1. Use um processo de demonstração com entrada climática em `27/05/2026 10:00`.
2. Registre a entrada seca incorretamente como `01/07/2026 12:00`.
3. Abra **Corrigir horários** e altere **Saída — Câmara climática** para
   `17/06/2026 10:00`.
4. Abra novamente e altere **Entrada — Câmara seca** para `17/06/2026 12:00`.
5. Confirme que a entrada climática original não mudou.
6. Confira no registro técnico os valores anterior e novo de cada correção.
7. Tente colocar a saída climática depois da entrada seca e confirme que a ordem inválida é
   recusada.

## 7. Formulário, navegação e Dashboard

1. Abra **Novo ensaio** e digite cliente, processo, produto e dados térmicos.
2. Sem salvar, abra **Agenda** e depois volte a **Novo ensaio**.
3. Confirme que os valores digitados foram restaurados.
4. Digite `01` em quantidade de amostras e confirme que o campo mostra `1`.
5. Confirme que o campo aceita no máximo dois dígitos e que o serviço recusa `0` e valores acima
   de `99`.
6. Role até o fim e confira se a barra não cobre o botão **Salvar ensaio**.
7. No Dashboard, clique em cada indicador e confira os filtros. Clique novamente para remover.
8. Passe o ponteiro pelos ícones `?` e confira os resumos contextuais.
9. Clique em **Created by Jhoncts** e confirme a abertura de `github.com/jhoncts`.
10. Reduza a janela até a largura mínima e confirme que a barra lateral mostra apenas os ícones,
    com o nome de cada opção no balão de ajuda.
11. Em uma janela larga, clique na seta do cabeçalho da barra lateral para recolhê-la. Confirme
    que ficam apenas ícones com balões de ajuda e que a tela/rolagem não muda.
12. Clique na seta para expandir e confirme que os textos voltam a aparecer.
13. Amplie novamente após o modo compacto automático e confirme que a preferência manual da
    barra completa ou recolhida reaparece sem perder o formulário aberto.
14. Confira Dashboard, Ensaios, Agenda, Usuários e Configurações nas duas larguras; cartões e
    botões devem quebrar de linha sem sobreposição.
15. No Dashboard, confira se os cartões **Câmara climática** e **Secagem** exibem ícone, estado,
    descrição e botão, sem retângulos cinza.
16. Pause a câmara com um motivo, confirme a indicação **Pausada** e depois use **Retomar**.
17. Abra **Atividades**, **Usuários** e um dia com prazos na **Agenda**; os cartões devem exibir
    todo o conteúdo, sem áreas cinza ou em branco.
18. Role uma tela longa até aproximadamente a metade e redimensione a janela lentamente perto da
    troca entre menu completo e compacto.
19. Em **Novo ensaio**, confira que identificação e configuração térmica ficam lado a lado numa
    janela larga e são empilhadas sem sobreposição ao reduzir a largura.
20. Confirme que **Observações** ocupa toda a largura do seu cartão e que a prévia mostra o Ts em
    destaque, com cartões próprios para câmara e secagem.
21. Em **Usuários**, abra **Editar** e confirme que nome/sobrenome e usuário/perfil compartilham
    linhas quando houver espaço, sem criar uma grande área vazia abaixo dos campos.
22. Em **Novo ensaio**, confira que “14 dias nominais • limite: 15 dias e 6 horas” aparece
    integralmente e faça a mesma verificação nos títulos, cartões e listas das demais telas.
23. Abra os diálogos de pausa, cancelamento e correção. Escolha um motivo pronto; depois selecione
    **Outros** e confirme que o campo livre aparece com limite de 180 caracteres.

Resultado esperado: a tela não deve piscar nem voltar ao topo. Os botões **Pausar** e **Retomar**
devem permanecer em uma linha, e a foto do usuário deve manter a borda circular sem serrilhado
visível.

## 8. Resumo térmico e redimensionamento

1. Abra um ensaio calculado por `Tamb + ΔT`.
2. Confirme que aparecem, abaixo do cabeçalho, o resumo, o caminho do ensaio, as condições, as
   ações operacionais e o registro técnico.
3. Confirme que o cartão de `Ts calculado` é o elemento principal do resumo.
4. Confira a equação com Tamb e Delta T, o EPL e a alternativa.
5. Reduza a janela e confirme que o cartão de Ts é empilhado sem cortar textos.
6. Abra um ensaio com Ts informado e outro personalizado.
7. Confira que câmara e secagem ficam lado a lado em uma janela larga, cada uma reunindo condição
   e cronograma; reduza a janela e confirme que os cartões são empilhados.
8. Confira que as opções de horário atual e manual ocupam toda a largura da área operacional.
9. Role até **Registro técnico detalhado** e confirme que os eventos usam a largura integral, com
   descrição à esquerda e responsável/data à direita.

Resultado esperado: Ts informado permanece em destaque; uma condição personalizada mostra a
referência textual sem inventar um valor numérico. Nenhuma parte da tela pode permanecer em
branco depois do cabeçalho.

## 9. Migração de uma cópia da v0.4.0

1. Feche o aplicativo.
2. Copie um banco de demonstração da v0.4.0 para uma nova pasta.
3. Aponte `CLIMATETEST_DATA_DIR` para essa nova pasta.
4. Abra a v0.5.0.
5. Crie o administrador inicial.
6. Confira ensaios, situações, prazos, pausas, agenda e atividades antigas.

Resultado esperado: nenhum ensaio é apagado ou recalculado apenas pela migração.

## 10. Notificações e e-mail sem janela de terminal

1. Gere o pacote com `.\scripts\build_windows.ps1`.
2. Abra `dist\ClimateTestManager-v0.5.0\ClimateTestManager.exe`.
3. Em **Configurações**, clique em **Ativar avisos**.
4. Desabilite temporariamente a tarefa no Agendador do Windows, reabra **Configurações** e
   confirme que o sistema mostra `Inativo`; reative-a pelo aplicativo antes de continuar.
5. Confira a tarefa:

```powershell
(Get-ScheduledTask -TaskName "ClimateTestManager-Notifications").Actions |
    Select-Object Execute, Arguments
```

O executável deve apontar para `ClimateTestNotifier.exe`. Não deve aparecer `powershell.exe`,
`cmd.exe` ou o caminho do projeto em `src`.

Para validar o e-mail:

1. Entre como administrador e abra **Configurações**.
2. Abra **Configurar e-mail** e expanda **Como configurar, passo a passo**.
3. Escolha o modelo Gmail, Microsoft 365 ou outro provedor e confirme o preenchimento sugerido.
4. Informe uma conta SMTP de teste. No Gmail, use senha de app; no Microsoft 365 corporativo,
   confirme com a TI se o SMTP autenticado está liberado. Cole a senha de app do Gmail com os
   espaços exibidos e confirme que o sistema os remove automaticamente.
5. Ative o envio, salve e confira na tela os destinatários automáticos e os destinatários do
   teste.
6. Use **Testar e-mail** e confirme que a janela de resultado mostra os endereços aceitos e um
   identificador de mensagem.
7. Verifique primeiro a caixa do remetente Gmail e depois as caixas dos usuários ativos.
8. Se o remetente receber e o endereço corporativo não, solicite à TI a verificação de filtro,
   quarentena e política de mensagens externas.
9. Abra **Guia de uso → Como configurar avisos por e-mail** e confira o mesmo fluxo.
10. Em um computador cujo nome do Windows contenha acento, confirme que o teste chega ao Gmail
   sem erro de codificação no comando `EHLO`.
11. Crie ao menos um operador ativo com outro endereço de teste.
12. Em um banco descartável, ajuste o relógio/estado até duas horas antes da retirada nominal.
13. Confirme que todos os usuários ativos recebem o resumo com cliente, produto, processo e
   quantidade.
14. Avance até depois do limite máximo e confirme o e-mail de atraso.

Não use senhas reais em capturas ou relatórios de teste.

## 11. Controle temporário de validação

O botão de avanço não aparece no uso normal. Para habilitá-lo somente no banco isolado:

```powershell
$env:CLIMATETEST_TEST_CONTROLS = "1"
flet run src/main.py
```

Confirme que o botão avança a etapa e atualiza a tela. Remova a variável antes de qualquer teste
com dados reais.

## 12. Backup

1. Feche e abra o sistema duas vezes no mesmo dia.
2. Abra a pasta de dados em **Configurações**.
3. Confirme que `backups` contém somente um arquivo automático referente ao dia.
4. Confirme que a pasta externa escolhida na instalação também contém somente uma cópia diária.
5. Use **Alterar pasta de backup** como administrador, selecione outra pasta de teste e confirme
   que a primeira cópia é criada imediatamente.
6. Use **Criar cópia de segurança** e escolha um terceiro destino.
7. Confirme que as cópias começam com um banco SQLite válido e abrem sem erro.
8. Ao lado de cada `climatetest_auto_*.db`, abra o respectivo `.db.manifest.json` e confirme:
   `quick_check` igual a `ok`, `foreign_key_violations` igual a `0`, versão do esquema `11` e
   um SHA-256 com 64 caracteres.
9. Calcule o SHA-256 do `.db` e compare com o manifesto.
10. Copie um backup para outra pasta isolada, aponte o sistema para a cópia e confirme login,
    ensaios, atividades e falhas. Registre data, executor e resultado desta restauração.

O banco ativo deve continuar no disco local. Não mova o arquivo aberto para o OneDrive; o sistema
deve recusar esse local durante a configuração inicial.

## 13. Falhas, ações corretivas e base normativa

1. Entre como Operador e abra **Configurações → Falhas do sistema**.
2. Registre uma falha fictícia com impacto, descrição e ação imediata.
3. Confirme que o registro mostra responsável e data.
4. Confirme que o Operador não consegue encerrar a falha.
5. Entre como Administrador, registre ação corretiva e encerre.
6. Confira que descrição e ação imediata originais não foram substituídas.
7. Na seção **Conformidade normativa e validação**, confira versão do software, esquema, regra,
   ABNT NBR ISO/IEC 17025:2017, ABNT NBR IEC 60079-0:2020 e referências complementares.
8. Confirme que a tela informa que o software apoia requisitos, mas não certifica nem acredita o
   laboratório.
9. Confira a pasta `documentacao-conformidade` no pacote e execute integralmente o protocolo
   `VALIDATION_PROTOCOL_V050.md`.

## 14. Qualidade automatizada

Antes do commit:

```powershell
ruff check .
ruff format --check .
pytest
git diff --check
git status
```

O resultado esperado nesta revisão é **142 testes aprovados**. Faça a validação final em Windows
porque o build, o SMTP protegido pela conta do Windows, as notificações e o Agendador de Tarefas
não podem ser exercitados integralmente no Linux.
