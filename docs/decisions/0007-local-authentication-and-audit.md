# ADR 0007 — Autenticação local e identidade da auditoria

## Status

Aceita para a v0.5.0.

## Contexto

As versões anteriores registravam ações humanas como `Não identificado`. O sistema precisa
atribuir mudanças a pessoas reais sem depender de serviços pagos, internet ou contas externas.

## Decisão

- Contas, sessões e eventos de segurança ficam no mesmo SQLite local.
- A primeira conta é administradora.
- Existem os perfis Administrador e Operador.
- Senhas usam PBKDF2-HMAC-SHA256 com salt individual e 600 mil iterações.
- Tokens de sessão são aleatórios; apenas SHA-256 do token é persistido no banco.
- O token completo só fica em `preferences.json` quando o usuário marca **Manter conectado**.
- Alteração de senha, redefinição administrativa e desativação revogam sessões.
- O serviço de ensaios recebe o ator autenticado por um provedor injetado.

## Consequências

- O sistema opera sem internet e sem armazenar senha em texto aberto.
- Quem possui acesso ao computador ainda precisa ser protegido pelas políticas do Windows.
- Recuperação de senha é uma ação administrativa local; não existe envio de senha por e-mail.
- Integrações futuras com Microsoft 365 devem usar OAuth e permanecer separadas da senha local.
