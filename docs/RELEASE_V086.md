# ClimateTest Manager v0.8.6 — R11

Esta versão promove o fluxo térmico e frio validado no Beta 6 e acrescenta distribuição global
de atualizações e isolamento rígido entre produtos da mesma família.

## Atualização global

- O cliente consulta uma Release estável ao iniciar e novamente a cada seis horas.
- A consulta usa `update-manifest.json`, publicado junto com o instalador.
- Tamanho, SHA-256 e assinatura Authenticode declarada são conferidos antes da execução.
- O papel servidor/estação e o endereço do servidor são preservados na instalação silenciosa.
- Estações aguardam o servidor central alcançar a revisão exigida pelo manifesto.
- A API de Releases permanece como fallback para atualizar instalações v0.8.5 já distribuídas.
- O workflow bloqueia uma tag oficial quando não há certificado de assinatura configurado.
- O GitHub gera atestado de proveniência para o instalador de uma Release oficial.

## Isolamento entre sistemas

- Identidade exclusiva: `com.jhoncts.climatetestmanager`.
- Endpoint obrigatório: `/climatetest-server.json`.
- O cliente rejeita qualquer servidor que declare produto, serviço ou protocolo diferentes.
- Descoberta UDP também inclui e valida o `product_id`.
- Mutex, mensagem e porta de ativação desktop são derivados da identidade do produto.
- O registro de portas e o checklist para futuros produtos estão em `PRODUCT_ISOLATION.md`.

## Sequência de implantação da v0.8.6

1. Criar e verificar um backup externo do servidor central.
2. Atualizar o servidor central e confirmar `v0.8.6 / R11-20260825`.
3. Confirmar `http://SERVIDOR:8550/climatetest-server.json` na rede do laboratório.
4. Atualizar as estações; nenhuma base SQLite deve ser copiada para elas.
5. Nas próximas versões, publicar uma tag estável será suficiente para avisar instalações em
   qualquer local com acesso HTTPS ao GitHub.

## Assinatura necessária para a publicação oficial

Cadastre no repositório os secrets `WINDOWS_SIGNING_CERTIFICATE_BASE64` e
`WINDOWS_SIGNING_CERTIFICATE_PASSWORD`. O timestamp pode ser personalizado por
`WINDOWS_SIGNING_TIMESTAMP_URL`. Certificados e senhas nunca devem ser commitados.
