# Histórico de versões

Todas as mudanças relevantes deste projeto serão registradas neste arquivo.

O formato segue o princípio do [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o projeto utiliza versionamento semântico.

## [Não publicado]

### Planejado

- Persistência do fluxo de câmara e secagem.
- Histórico auditável de alterações.

## [0.3.0] - 2026-07-22

### Adicionado

- Conversão operacional das permanências em dias nominais e limite com tolerância.
- Normalização imediata das entradas decimais para o padrão brasileiro.
- Filtros que removem caracteres não numéricos de Tamb e Delta T.

### Alterado

- Exemplo do processo atualizado para `26123.1`, com limite de 10 caracteres, conteúdo livre e
  contador oculto para preservar o alinhamento da tela.
- Valores decimais apresentados com vírgula na interface.
- Mensagem do dashboard esclarece a persistência local e as regras versionadas da Tabela 17.

### Removido

- Campo Marcação Ex da tela e do caso de uso de cadastro; somente o EPL é necessário para a
  determinação das condições climáticas.

## [0.2.1] - 2026-07-21

### Corrigido

- Liberação explícita da conexão SQLite ao fechar a aplicação.
- Limpeza dos bancos temporários nos testes executados no Windows.
- Exibição de valores inteiros terminados em zero, como 90 °C, 90% UR e Ts de 140 °C.

### Alterado

- Integração contínua executada em Linux e Windows para detectar diferenças entre plataformas.
- Tamb máxima passa a adotar +40 °C, de forma visível e auditável, quando não informada pelo
  cliente.

## [0.2.0] - 2026-07-21

### Adicionado

- Formulário profissional de cadastro de ensaios.
- Cálculo interativo de Ts e das condições da Tabela 17.
- Escolha do operador entre as opções A e B quando ambas são válidas.
- Leitura de ponto ou vírgula como separador decimal.
- Persistência da fotografia normativa aplicada a cada ensaio.
- Registro automático do evento de criação na auditoria.
- Dashboard conectado aos cadastros recentes.
- Navegação funcional entre dashboard e novo ensaio.
- Testes integrados do serviço, banco e montagem da aplicação.

## [0.1.0] - 2026-07-21

### Adicionado

- Estrutura profissional baseada no padrão `src`.
- Janela desktop inicial em Flet.
- Configuração local do SQLite na pasta de dados do usuário.
- Modelos iniciais de ensaio e evento de auditoria.
- Motor da Tabela 17 com opções A e B.
- Interpretação operacional de `Ts = 75 °C` na faixa superior.
- Testes unitários das principais fronteiras normativas.
- Configuração de Pytest, Ruff e integração contínua.
- Script de empacotamento para Windows com PyInstaller.
