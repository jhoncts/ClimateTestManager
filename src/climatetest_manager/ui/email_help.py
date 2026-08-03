"""Conteúdo único do tutorial de avisos por e-mail."""

EMAIL_SETUP_STEPS = (
    "Entre como administrador e abra Configurações → Avisos por e-mail.",
    "Escolha um modelo de provedor ou obtenha servidor, porta e usuário SMTP com a TI.",
    "Preencha o e-mail remetente e o usuário SMTP. Normalmente ambos são o e-mail completo.",
    "Informe a senha SMTP. No Gmail, use uma senha de app criada com a verificação em duas etapas; "
    "os espaços exibidos pelo Google são removidos automaticamente.",
    "Mantenha TLS ativado na porta 587, salvo se o provedor ou a TI informar outra configuração.",
    "Ative “Enviar e-mails automáticos”, salve e clique em “Testar e-mail”.",
    "No resultado do teste, confira os destinatários aceitos e procure primeiro a cópia enviada "
    "ao próprio remetente.",
    "Ative também os avisos em segundo plano; eles executam as verificações a cada 5 minutos.",
)

EMAIL_PROVIDER_NOTES = (
    (
        "Gmail",
        "Servidor smtp.gmail.com, porta 587 e TLS. A conta precisa de verificação "
        "em duas etapas e senha de app; não use a senha normal da conta.",
    ),
    (
        "Microsoft 365 corporativo",
        "Servidor smtp.office365.com, porta 587 e TLS. O SMTP autenticado pode estar "
        "bloqueado pela empresa; peça à TI uma conta autorizada. Esta versão usa "
        "usuário e senha SMTP e não implementa OAuth2.",
    ),
    (
        "Outro provedor",
        "Solicite ao provedor ou à TI o servidor SMTP, a porta, o uso de TLS e a "
        "credencial destinada ao sistema.",
    ),
)
