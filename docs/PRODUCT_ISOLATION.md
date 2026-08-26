# Isolamento entre produtos da família

Cada produto deve ter uma identidade técnica própria. Compartilhar Flet, Python, SQLite ou o
modelo servidor/estação é permitido; compartilhar identificadores operacionais não é.

## Registro atual

| Produto | Product ID | TCP | Descoberta | Identidade HTTP | ProgramData |
|---|---|---:|---:|---|---|
| ClimateTest Manager | `com.jhoncts.climatetestmanager` | 8550 | UDP 8551 | `/climatetest-server.json` | `ClimateTestManager` |
| CalibraLab | `com.jhoncts.calibralab` | 8765 | Reservar 8766 | `/calibralab-server.json` | `CalibraLab` |

O cliente deve consultar o arquivo de identidade antes de incorporar qualquer interface. Uma
resposta HTTP genérica ou uma página Flet na porta informada não é suficiente. O cliente do
ClimateTest exige simultaneamente:

```json
{
  "product_id": "com.jhoncts.climatetestmanager",
  "service": "ClimateTestManager",
  "protocol": 1
}
```

Se qualquer campo divergir, a conexão é recusada. Assim, até uma configuração manual apontando
para a porta de outro sistema não pode exibir a tela errada.

## Checklist obrigatório para um produto novo

1. Criar um `product_id` em domínio reverso, por exemplo `com.jhoncts.novoproduto`.
2. Reservar uma porta TCP e, se houver descoberta, a porta UDP seguinte.
3. Criar um arquivo de identidade HTTP exclusivo e validá-lo antes da página principal.
4. Usar pasta própria em `C:\ProgramData`, `%LOCALAPPDATA%` e cache do usuário.
5. Usar prefixo exclusivo para variáveis de ambiente, logs e arquivos de configuração.
6. Usar `AppId`, nome de atalho, regra de firewall e tarefas agendadas exclusivos.
7. Derivar mutex, mensagem e porta de ativação do `product_id`; nunca copiar um número fixo.
8. Usar repositório, manifesto e canal de atualização próprios.
9. Adicionar um teste negativo que aponte o cliente para cada outro produto da família.

O arquivo `product_identity.py` do ClimateTest concentra esses valores. Ao iniciar outro produto,
crie um arquivo equivalente e trate a alteração desses campos como parte obrigatória do scaffold.
