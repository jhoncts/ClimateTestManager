# ClimateTest Manager v0.8.5 — R9

Esta é a candidata final para implantação no laboratório. A versão resolve as regressões visuais
que ainda apareciam na v0.8.4 e acrescenta uma proteção explícita contra cliente, servidor ou
arquivos antigos sendo aceitos como instalação nova.

## Interface validada

- O menu lateral mantém ícones, textos e badge em notebooks e na largura mínima suportada.
- O Novo ensaio tem uma única rolagem e uma árvore persistente, sem desmontar o conteúdo ao
  digitar, selecionar, alternar visualizações ou rolar.
- Identificação, Configuração térmica, Informações complementares e Condição aplicada usam cards
  compactos e ícones semânticos em todos os seis temas.
- A Tabela 17 reage ao Ts, mostra a faixa correspondente de cada EPL, reduz visualmente as opções
  incompatíveis e permite selecionar diretamente uma única combinação EPL/alternativa.
- A visualização simples apresenta o resumo operacional; a avançada mantém a tabela normativa.
- O menu Ações é ancorado ao botão e informa por que uma ação está indisponível.
- Cancelamento e exclusão usam uma confirmação por pressão de 1,6 segundo, com percentual e
  cancelamento imediato ao soltar.

## Atualização e rede

Use `ClimateTestManager-Setup-v0.8.5.exe` em todas as máquinas:

1. Execute o instalador por cima da instalação existente no **Servidor central**.
2. Não desinstale a versão anterior e não apague `C:\ProgramData\ClimateTestManager`.
3. Abra o sistema e confirme no rodapé `v0.8.5` e `R9-20260814`.
4. Atualize cada **Estação de trabalho** com o mesmo instalador.

O instalador apaga apenas os arquivos de programa conhecidos antes de copiar os novos. Banco,
fotos, preferências e backups permanecem no ProgramData. O servidor é considerado pronto apenas
quando responde com a revisão exata `R9-20260814`; uma estação não continua silenciosamente com
um servidor antigo.

## Topologia suportada

- Exatamente um computador da rede deve ser configurado como **Servidor central**.
- Cada computador de uso recebe o aplicativo, mas os demais são **Estações de trabalho**.
- Somente o servidor mantém o SQLite, tarefas de servidor, notificador e backups centrais.
- As estações usam o nome ou IP do servidor; não criam bancos paralelos.
- A descoberta de outro servidor bloqueia a criação acidental de um segundo servidor central.

## Verificações da candidata

- Ruff para lint e formatação.
- 214 testes Python aprovados e 1 teste dependente de plataforma ignorado, incluindo regressões
  de árvore única, sidebar, temas, Tabela 17, popup de ações, confirmação por pressão, histórico
  de pausa e revisão do servidor.
- Smoke test do servidor empacotado e da janela desktop real.
- Instalação silenciosa como estação e teste da conexão persistida.
- Atualização por cima de um servidor em execução, preservando o ProgramData.
- Conferência SHA-256 do instalador publicado.

## Aceite local recomendado

- confirmar `v0.8.5 / R9-20260814` no servidor e nas estações;
- cadastrar um ensaio em cada modo e salvar um caso pela Tabela 17;
- testar Ts abaixo, dentro e acima das faixas para observar alternativas desabilitadas;
- recolher e expandir a lateral, minimizar, restaurar e rolar o Novo ensaio;
- pausar e retomar cada câmara e conferir o Registro de atividades;
- abrir o menu Ações e concluir um cancelamento controlado;
- registrar e resolver uma falha, testar SMTP e gerar um backup externo.
