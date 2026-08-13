# ClimateTest Manager v0.8.4 — R8

Esta versão corrige as regressões encontradas na validação real da v0.8.3/R7 e é a candidata para
uso controlado no laboratório.

## O que mudou

- A tela inicial e a navegação não desmontam mais a moldura do aplicativo.
- A barra lateral mantém textos e badges ao navegar, redimensionar, minimizar ou restaurar.
- A troca de telas deixa de animar a árvore inteira; os feedbacks locais continuam leves.
- O Novo ensaio usa um único scroll vertical e segue o layout compacto em duas colunas.
- A visualização avançada da Tabela 17 permanece montada, sem desaparecer durante a rolagem.
- O modo Tabela 17 recebe um Ts, um EPL e uma condição; incompatibilidades são explicadas.
- Configurações usa cards 2×2 e mantém o histórico de falhas em uma janela própria.
- O fluxo SMTP não confunde mais teste de credenciais com envio automático ativo.
- Uma falha registrada gera aviso interno e tenta o e-mail imediatamente, sem falhar em silêncio.
- Resolver uma falha fecha a confirmação e atualiza o log.
- A confirmação de ações perigosas mostra o progresso dentro do próprio botão.

## Implantação em rede

Use `ClimateTestManager-Setup-v0.8.4.exe` em todas as máquinas:

1. Instale ou atualize primeiro o computador que ficará como **Servidor central**.
2. Confirme que o ClimateTest Manager abre normalmente nesse computador.
3. Instale as demais máquinas como **Estação de trabalho**; o instalador procura o servidor e
   também aceita o nome ou IP quando necessário.
4. Nunca desinstale a versão anterior para atualizar e nunca apague
   `C:\ProgramData\ClimateTestManager`.

O instalador impede uma nova instalação de servidor quando encontra outro servidor central na
rede. As estações não recebem cópia do SQLite: toda gravação é processada pelo servidor.

## Verificações automatizadas

- Ruff (lint e formatação).
- 206 testes Python aprovados e 1 teste dependente de plataforma ignorado.
- Smoke test do servidor empacotado e da janela desktop real.
- Instalação silenciosa como estação e verificação do servidor persistido.
- Atualização por cima de um servidor existente, com retomada na porta 8550.
- Conferência do instalador pelo SHA-256 publicado.

## Aceite local recomendado

Antes de liberar para dados reais, faça uma passagem curta em uma cópia do ambiente:

- abrir sem redimensionar a janela;
- recolher/expandir a sidebar e testar janela maximizada e restaurada;
- alternar várias vezes entre a visualização simples e avançada do Novo ensaio;
- registrar e resolver uma falha;
- confirmar o recebimento do e-mail da falha;
- criar um backup externo e verificar seu manifesto;
- abrir simultaneamente uma estação e o servidor.
