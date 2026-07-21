# Guia de desenvolvimento

## 1. Ambiente virtual

O ambiente virtual cria uma instalação de Python isolada para este projeto. Assim, atualizar uma
biblioteca do ClimateTest Manager não interfere em outros programas.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Quando `(.venv)` aparecer no início da linha do terminal, o ambiente está ativado.

## 2. Instalação editável

```powershell
pip install -e ".[dev]"
```

- `-e` instala o projeto em modo editável: alterações no código aparecem sem reinstalação.
- `.[dev]` inclui as ferramentas de teste, formatação e empacotamento.
- As versões ficam centralizadas em `pyproject.toml`.

## 3. Executar

```powershell
flet run src/main.py
```

## 4. Testar

```powershell
pytest
```

Um teste automatizado descreve uma expectativa reproduzível. Exemplo: ao usar EPL Gc e
`Ts = 80 °C`, somente a opção A deve estar disponível.

## 5. Formatar e analisar

```powershell
ruff format .
ruff check .
```

O formatador cuida da apresentação do código. O analisador identifica erros comuns, imports não
utilizados e construções difíceis de manter.

## 6. Fluxo de Git sugerido

```powershell
git status
git add .
git commit -m "feat: cria estrutura inicial do projeto"
```

Faça commits pequenos e coerentes. O prefixo indica a intenção:

- `feat`: nova funcionalidade;
- `fix`: correção;
- `test`: testes;
- `docs`: documentação;
- `refactor`: melhoria interna sem alterar o comportamento;
- `chore`: manutenção e ferramentas.

## 7. Empacotar

```powershell
.\scripts\build_windows.ps1
```

O PyInstaller não faz compilação cruzada. O `.exe` final deve ser gerado no Windows onde será
usado ou em outra máquina Windows compatível.
