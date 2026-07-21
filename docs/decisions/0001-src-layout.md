# ADR 0001 — Adotar estrutura `src`

- Status: aceito
- Data: 2026-07-21

## Contexto

O projeto deve servir como aplicação interna e como portfólio profissional.

## Decisão

Manter o pacote Python em `src/climatetest_manager` e um ponto de entrada fino em `src/main.py`.

## Consequências

- Testes verificam o pacote instalado, reduzindo imports acidentais.
- O Flet continua encontrando um `main.py` simples para execução e empacotamento.
- A estrutura inicial possui um nível adicional de diretórios, mas escala melhor.
