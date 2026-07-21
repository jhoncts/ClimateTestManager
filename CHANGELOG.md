# Histórico de versões

Todas as mudanças relevantes deste projeto serão registradas neste arquivo.

O formato segue o princípio do [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o projeto utiliza versionamento semântico.

## [Não publicado]

### Planejado

- Persistência do fluxo de câmara e secagem.
- Histórico auditável de alterações.

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
