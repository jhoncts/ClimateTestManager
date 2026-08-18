# Atualizações do ClimateTest Manager

## Como funciona para quem usa o programa

Depois que uma máquina possui uma versão com o atualizador integrado, não é necessário enviar o
novo instalador manualmente para cada computador.

Na abertura, o cliente consulta a Release mais recente do repositório. Se existir uma versão mais
nova, ele apresenta um aviso dentro da janela do ClimateTest Manager. O usuário pode baixar a
atualização; antes de executar o instalador, o aplicativo confere o SHA-256 publicado. O Windows
então pede autorização de administrador (UAC) e o instalador atualiza a instalação existente,
preservando banco, configuração e papel da máquina.

Sem acesso à internet, essa consulta é simplesmente ignorada. O uso do servidor e das estações na
rede local não depende do GitHub.

## Como publicar uma atualização

A versão do projeto deve ser alterada antes da publicação, por exemplo de `0.8.0` para `0.8.1`.
Faça a alteração, valide os testes, faça merge na `main` e atualize sua cópia local:

```powershell
cd "C:\Scripts\ClimateTestManager\ClimateTestManager"
git switch main
git pull --ff-only origin main
```

Primeiro confira sem publicar nada:

```powershell
.\scripts\publish_release.ps1
```

Quando a mensagem confirmar que a versão está pronta:

```powershell
.\scripts\publish_release.ps1 -Push
```

O script cria e envia somente a tag da versão. O GitHub Actions faz o trabalho pesado:

1. executa lint, formatação e testes;
2. empacota cliente, servidor e notificador;
3. compila o instalador Windows;
4. testa a instalação como estação e como servidor;
5. confere o SHA-256;
6. cria a GitHub Release com os arquivos validados.

Se qualquer teste falhar, a Release não deve ser utilizada. Corrija o problema e publique uma nova
versão; não substitua silenciosamente um instalador que já foi anunciado com o mesmo número.

## Política prática de versões

- `0.8.1`: correções pequenas e seguras, sem mudança relevante de uso.
- `0.9.0`: funcionalidade nova ou mudança maior ainda dentro da fase pré-1.0.
- `1.0.0`: primeira versão formalmente congelada/validada para uso controlado em produção.

Nunca reutilize uma tag já publicada para um binário diferente. Isso mantém a atualização
auditável e evita que duas máquinas tenham arquivos distintos apresentados como a mesma versão.
