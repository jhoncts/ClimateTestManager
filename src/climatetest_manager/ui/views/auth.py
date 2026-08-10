"""Telas de primeiro acesso e autenticação local."""

from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

import flet as ft

from climatetest_manager.services.auth import UserRegistrationCommand
from climatetest_manager.ui.theme import AppColors


def _security_item(icon: ft.IconData, text: str) -> ft.Container:
    """Mantém as mensagens da lateral legíveis e contidas no próprio cartão."""

    return ft.Container(
        border_radius=11,
        bgcolor="#145E5C",
        border=ft.Border.all(1, "#318985"),
        padding=ft.Padding.symmetric(horizontal=11, vertical=9),
        margin=ft.Margin.only(right=4),
        content=ft.Row(
            spacing=9,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(icon, size=19, color="#99F6E4"),
                ft.Text(
                    text,
                    size=11,
                    color="#ECFEFF",
                    expand=True,
                ),
            ],
        ),
    )


def _brand() -> ft.Column:
    return ft.Column(
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        spacing=14,
        controls=[
            ft.Container(
                width=72,
                height=72,
                border_radius=18,
                bgcolor=AppColors.WHITE,
                padding=5,
                alignment=ft.Alignment.CENTER,
                content=ft.Image(
                    src="brand/climatetest-logo.png",
                    fit=ft.BoxFit.CONTAIN,
                    semantics_label="Logo do ClimateTest Manager",
                ),
            ),
            ft.Text(
                "ClimateTest Manager",
                size=28,
                weight=ft.FontWeight.BOLD,
                color=AppColors.WHITE,
            ),
            ft.Text(
                "Controle seguro e rastreável de ensaios climáticos.",
                size=14,
                color="#CCFBF1",
            ),
            ft.Container(height=6),
            _security_item(
                ft.Icons.LOCK_OUTLINE,
                "Acesso permitido somente a usuários cadastrados.",
            ),
            _security_item(
                ft.Icons.VERIFIED_USER_OUTLINED,
                "Ações vinculadas ao responsável autenticado.",
            ),
            _security_item(
                ft.Icons.STORAGE_OUTLINED,
                "Contas e senhas protegidas no banco local.",
            ),
        ],
    )


def _auth_shell(content: ft.Control) -> ft.Container:
    return ft.Container(
        expand=True,
        bgcolor=AppColors.PAGE_BACKGROUND,
        alignment=ft.Alignment.CENTER,
        padding=24,
        content=ft.Container(
            width=1040,
            height=680,
            border_radius=24,
            bgcolor=AppColors.SURFACE,
            shadow=ft.BoxShadow(
                blur_radius=34,
                spread_radius=1,
                color="#220F172A",
                offset=ft.Offset(0, 12),
            ),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.ResponsiveRow(
                spacing=0,
                run_spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Container(
                        col={"xs": 12, "md": 5, "lg": 4},
                        height=680,
                        padding=34,
                        gradient=ft.LinearGradient(
                            begin=ft.Alignment.TOP_LEFT,
                            end=ft.Alignment.BOTTOM_RIGHT,
                            colors=["#087E8B", "#102A43"],
                        ),
                        content=_brand(),
                    ),
                    ft.Container(
                        col={"xs": 12, "md": 7, "lg": 8},
                        height=680,
                        padding=36,
                        content=content,
                    ),
                ],
            ),
        ),
    )


class LoginView:
    """Coleta credenciais sem revelar se usuário ou e-mail existem."""

    def __init__(
        self,
        on_login: Callable[[str, str, bool], None],
        *,
        on_recover_admin: Callable[[str, UserRegistrationCommand], str] | None = None,
        allow_remember: bool = True,
    ) -> None:
        self._on_login = on_login
        self._on_recover_admin = on_recover_admin
        self.login = ft.TextField(
            label="Usuário ou e-mail",
            prefix_icon=ft.Icons.PERSON_OUTLINE,
            autofocus=True,
            max_length=254,
            counter="",
            border_radius=10,
        )
        self.password = ft.TextField(
            label="Senha",
            prefix_icon=ft.Icons.LOCK_OUTLINE,
            password=True,
            can_reveal_password=True,
            max_length=128,
            counter="",
            border_radius=10,
            on_submit=lambda _event: self._submit(),
        )
        self.remember = ft.Checkbox(
            label="Manter conectado neste computador por 30 dias",
            value=False,
            visible=allow_remember,
        )
        self.error = ft.Text("", size=12, color=AppColors.DANGER)
        self.root = _auth_shell(
            ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                spacing=18,
                controls=[
                    ft.Text(
                        "Bem-vindo de volta",
                        size=27,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        "Entre com o usuário ou e-mail cadastrado pelo administrador.",
                        size=13,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                    ft.Container(height=4),
                    self.login,
                    self.password,
                    self.remember,
                    self.error,
                    ft.Button(
                        content="Entrar",
                        icon=ft.Icons.LOGIN,
                        height=46,
                        bgcolor=AppColors.PRIMARY,
                        color=AppColors.WHITE,
                        tooltip="Validar as credenciais e abrir o sistema",
                        on_click=lambda _event: self._submit(),
                    ),
                    *(
                        [
                            ft.TextButton(
                                content="Recuperar administrador neste servidor",
                                icon=ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
                                on_click=self._show_recovery_dialog,
                            )
                        ]
                        if self._on_recover_admin is not None
                        else []
                    ),
                    ft.Container(
                        border_radius=12,
                        bgcolor=AppColors.INFO_LIGHT,
                        padding=12,
                        content=ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(
                                    ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
                                    color=AppColors.INFO,
                                    size=19,
                                ),
                                ft.Text(
                                    "Novas contas só podem ser criadas dentro da área "
                                    "administrativa.",
                                    size=11,
                                    color=AppColors.TEXT_PRIMARY,
                                    expand=True,
                                ),
                            ],
                        ),
                    ),
                ],
            )
        )

    def _submit(self) -> None:
        self.error.value = ""
        try:
            self._on_login(
                self.login.value,
                self.password.value,
                bool(self.remember.value),
            )
        except ValueError as error:
            self.error.value = str(error)
            with suppress(RuntimeError):
                self.error.update()

    def _show_recovery_dialog(self, _event: object | None = None) -> None:
        if self._on_recover_admin is None:
            return
        recovery_code = ft.TextField(
            label="Código de recuperação",
            hint_text="CTM-XXXX-XXXX-XXXX-XXXX-XXXX",
            max_length=32,
            counter="",
        )
        first_name = ft.TextField(label="Nome correto", max_length=80, counter="")
        last_name = ft.TextField(label="Sobrenome correto", max_length=120, counter="")
        username = ft.TextField(label="Novo usuário", max_length=32, counter="")
        email = ft.TextField(label="Novo e-mail", max_length=254, counter="")
        password = ft.TextField(
            label="Nova senha",
            password=True,
            can_reveal_password=True,
            max_length=128,
            counter="",
        )
        confirmation = ft.TextField(
            label="Confirmar nova senha",
            password=True,
            can_reveal_password=True,
            max_length=128,
            counter="",
        )
        error_text = ft.Text("", size=11, color=AppColors.DANGER)
        page = self.root.page

        def confirm(_confirm_event: object | None = None) -> None:
            command = UserRegistrationCommand(
                username=username.value,
                email=email.value,
                first_name=first_name.value,
                last_name=last_name.value,
                password=password.value,
                password_confirmation=confirmation.value,
                role="admin",
            )
            try:
                next_code = self._on_recover_admin(recovery_code.value, command)
            except ValueError as error:
                error_text.value = str(error)
                error_text.update()
                return
            page.pop_dialog()
            page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Administrador recuperado"),
                    content=ft.Column(
                        width=520,
                        tight=True,
                        spacing=12,
                        controls=[
                            ft.Text(
                                "Entre com os novos dados. O código anterior foi invalidado; "
                                "guarde o novo código em local seguro fora do computador.",
                            ),
                            ft.Container(
                                border_radius=12,
                                bgcolor=AppColors.INFO_LIGHT,
                                padding=14,
                                content=ft.Text(
                                    next_code,
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    selectable=True,
                                ),
                            ),
                        ],
                    ),
                    actions=[
                        ft.Button(
                            content="Entendi",
                            on_click=lambda _event: page.pop_dialog(),
                        )
                    ],
                )
            )

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Recuperar administrador"),
                content=ft.Column(
                    width=580,
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=11,
                    controls=[
                        ft.Text(
                            "Disponível somente no computador servidor. A conta principal "
                            "será corrigida, todas as sessões antigas serão encerradas e o "
                            "código será renovado.",
                            size=12,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        recovery_code,
                        ft.ResponsiveRow(
                            controls=[
                                ft.Container(col={"xs": 12, "sm": 6}, content=first_name),
                                ft.Container(col={"xs": 12, "sm": 6}, content=last_name),
                            ]
                        ),
                        username,
                        email,
                        password,
                        confirmation,
                        error_text,
                    ],
                ),
                actions=[
                    ft.TextButton(
                        content="Cancelar",
                        on_click=lambda _event: page.pop_dialog(),
                    ),
                    ft.Button(
                        content="Recuperar e invalidar sessões",
                        icon=ft.Icons.SECURITY,
                        bgcolor=AppColors.DANGER,
                        color=AppColors.WHITE,
                        on_click=confirm,
                    ),
                ],
            )
        )


class InitialSetupView:
    """Cria a primeira conta, que obrigatoriamente será administradora."""

    def __init__(
        self,
        on_create_admin: Callable[[UserRegistrationCommand], None],
    ) -> None:
        self._on_create_admin = on_create_admin
        self.first_name = ft.TextField(
            label="Nome",
            max_length=80,
            counter="",
            border_radius=10,
            expand=True,
        )
        self.last_name = ft.TextField(
            label="Sobrenome",
            max_length=120,
            counter="",
            border_radius=10,
            expand=True,
        )
        self.username = ft.TextField(
            label="Nome de usuário",
            hint_text="Ex.: jhon.cleiton",
            max_length=32,
            counter="",
            border_radius=10,
        )
        self.email = ft.TextField(
            label="E-mail",
            keyboard_type=ft.KeyboardType.EMAIL,
            max_length=254,
            counter="",
            border_radius=10,
        )
        self.password = ft.TextField(
            label="Senha",
            password=True,
            can_reveal_password=True,
            max_length=128,
            counter="",
            border_radius=10,
        )
        self.confirmation = ft.TextField(
            label="Confirmar senha",
            password=True,
            can_reveal_password=True,
            max_length=128,
            counter="",
            border_radius=10,
            on_submit=lambda _event: self._submit(),
        )
        self.error = ft.Text("", size=12, color=AppColors.DANGER)
        self.root = _auth_shell(
            ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                spacing=13,
                controls=[
                    ft.Text(
                        "Configuração do primeiro acesso",
                        size=25,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        "Cadastre o responsável inicial. Esta será a única etapa aberta "
                        "de criação de conta; depois, somente administradores poderão "
                        "cadastrar novos usuários.",
                        size=13,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                    ft.ResponsiveRow(
                        spacing=12,
                        run_spacing=12,
                        controls=[
                            ft.Container(
                                col={"xs": 12, "sm": 6},
                                content=self.first_name,
                            ),
                            ft.Container(
                                col={"xs": 12, "sm": 6},
                                content=self.last_name,
                            ),
                        ],
                    ),
                    self.username,
                    self.email,
                    self.password,
                    self.confirmation,
                    ft.Text(
                        "Use no mínimo 8 caracteres, com pelo menos uma letra e um número.",
                        size=11,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                    self.error,
                    ft.Button(
                        content="Criar administrador e continuar",
                        icon=ft.Icons.ADMIN_PANEL_SETTINGS,
                        height=46,
                        bgcolor=AppColors.PRIMARY,
                        color=AppColors.WHITE,
                        tooltip="Criar a conta administradora inicial e acessar o sistema",
                        on_click=lambda _event: self._submit(),
                    ),
                    ft.Container(height=4),
                ],
            )
        )

    def _submit(self) -> None:
        self.error.value = ""
        command = UserRegistrationCommand(
            username=self.username.value,
            email=self.email.value,
            first_name=self.first_name.value,
            last_name=self.last_name.value,
            password=self.password.value,
            password_confirmation=self.confirmation.value,
            role="admin",
        )
        try:
            self._on_create_admin(command)
        except ValueError as error:
            self.error.value = str(error)
            with suppress(RuntimeError):
                self.error.update()


def build_login_view(
    on_login: Callable[[str, str, bool], None],
    *,
    on_recover_admin: Callable[[str, UserRegistrationCommand], str] | None = None,
    allow_remember: bool = True,
) -> ft.Container:
    return LoginView(
        on_login,
        on_recover_admin=on_recover_admin,
        allow_remember=allow_remember,
    ).root


def build_initial_setup_view(
    on_create_admin: Callable[[UserRegistrationCommand], None],
) -> ft.Container:
    return InitialSetupView(on_create_admin).root


def build_server_waiting_view() -> ft.Container:
    """Impede que uma conexão remota assuma o primeiro administrador."""

    return _auth_shell(
        ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            spacing=16,
            controls=[
                ft.Icon(ft.Icons.LAN_OUTLINED, size=52, color=AppColors.PRIMARY),
                ft.Text(
                    "Servidor aguardando configuração local",
                    size=25,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Por segurança, somente o navegador aberto no próprio computador servidor "
                    "pode escolher o armazenamento e criar o primeiro administrador.",
                    size=13,
                    color=AppColors.TEXT_SECONDARY,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(
                    border_radius=12,
                    bgcolor=AppColors.INFO_LIGHT,
                    padding=14,
                    content=ft.Text(
                        "Depois da configuração, atualize esta página e entre com a conta "
                        "fornecida pelo administrador.",
                        size=12,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ),
            ],
        )
    )


class StorageSetupView:
    """Pede ao responsável uma decisão consciente antes de criar ou abrir o banco."""

    def __init__(
        self,
        *,
        default_data_directory: Path,
        suggested_backup_directory: Path | None,
        on_confirm: Callable[[Path, Path | None], None],
    ) -> None:
        self._on_confirm = on_confirm
        self.data_directory = ft.TextField(
            label="Pasta local do banco de dados *",
            value=str(default_data_directory),
            hint_text="Ex.: C:\\ClimateTestManager\\Dados",
            max_length=500,
            counter="",
            border_radius=10,
            expand=True,
        )
        self.backup_directory = ft.TextField(
            label="Pasta das cópias de segurança no OneDrive (recomendado)",
            value=str(suggested_backup_directory or ""),
            hint_text="Ex.: C:\\Users\\Nome\\OneDrive - Empresa\\ClimateTestManager\\Backups",
            max_length=500,
            counter="",
            border_radius=10,
            expand=True,
        )
        self.acknowledgement = ft.Checkbox(
            label=(
                "Entendi: o banco ativo ficará no disco local e o OneDrive receberá apenas "
                "cópias de segurança."
            ),
            value=False,
        )
        self.error = ft.Text("", size=12, color=AppColors.DANGER)
        self.root = _auth_shell(
            ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                spacing=13,
                controls=[
                    ft.Text(
                        "Onde os dados serão protegidos?",
                        size=25,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        "O responsável pela instalação define estes locais uma única vez, "
                        "antes da criação do administrador principal.",
                        size=13,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                    ft.Container(
                        border_radius=12,
                        bgcolor=AppColors.INFO_LIGHT,
                        padding=12,
                        content=ft.Row(
                            spacing=9,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.Icon(ft.Icons.STORAGE_OUTLINED, color=AppColors.INFO, size=20),
                                ft.Text(
                                    "Banco local: usado pelo sistema e pelo notificador. "
                                    "Escolha uma pasta estável deste computador.",
                                    size=11,
                                    color=AppColors.TEXT_PRIMARY,
                                    expand=True,
                                ),
                            ],
                        ),
                    ),
                    ft.Row(
                        controls=[
                            self.data_directory,
                            ft.Button(
                                content="Escolher",
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=self._choose_data_directory,
                            ),
                        ]
                    ),
                    ft.Container(
                        border_radius=12,
                        bgcolor=AppColors.WARNING_LIGHT,
                        padding=12,
                        content=ft.Row(
                            spacing=9,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.Icon(ft.Icons.BACKUP, color=AppColors.WARNING, size=20),
                                ft.Text(
                                    "Backup no OneDrive: protege contra defeito ou perda da "
                                    "máquina. O arquivo aberto do banco não será sincronizado.",
                                    size=11,
                                    color=AppColors.TEXT_PRIMARY,
                                    expand=True,
                                ),
                            ],
                        ),
                    ),
                    ft.Row(
                        controls=[
                            self.backup_directory,
                            ft.Button(
                                content="Escolher",
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=self._choose_backup_directory,
                            ),
                        ]
                    ),
                    ft.Text(
                        "Se o OneDrive ainda não estiver configurado, este campo pode ficar "
                        "em branco. O sistema continuará mantendo 30 backups locais.",
                        size=10,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                    self.acknowledgement,
                    self.error,
                    ft.Button(
                        content="Salvar locais e continuar",
                        icon=ft.Icons.CHECK,
                        height=46,
                        bgcolor=AppColors.PRIMARY,
                        color=AppColors.WHITE,
                        on_click=lambda _event: self._submit(),
                    ),
                ],
            )
        )

    async def _choose_data_directory(self, _event: object | None = None) -> None:
        path = await ft.FilePicker().get_directory_path(
            dialog_title="Escolha uma pasta local para o banco de dados"
        )
        if path:
            self.data_directory.value = path
            self.data_directory.update()

    async def _choose_backup_directory(self, _event: object | None = None) -> None:
        path = await ft.FilePicker().get_directory_path(
            dialog_title="Escolha a pasta de backup no OneDrive"
        )
        if path:
            self.backup_directory.value = path
            self.backup_directory.update()

    def _submit(self) -> None:
        self.error.value = ""
        if not self.data_directory.value.strip():
            self.error.value = "Escolha a pasta local onde o banco será mantido."
        elif not self.acknowledgement.value:
            self.error.value = "Confirme que compreendeu a separação entre banco e backup."
        else:
            try:
                self._on_confirm(
                    Path(self.data_directory.value.strip()),
                    (
                        Path(self.backup_directory.value.strip())
                        if self.backup_directory.value.strip()
                        else None
                    ),
                )
                return
            except (OSError, ValueError) as error:
                self.error.value = str(error)
        with suppress(RuntimeError):
            self.error.update()


def build_storage_setup_view(
    *,
    default_data_directory: Path,
    suggested_backup_directory: Path | None,
    on_confirm: Callable[[Path, Path | None], None],
) -> ft.Container:
    return StorageSetupView(
        default_data_directory=default_data_directory,
        suggested_backup_directory=suggested_backup_directory,
        on_confirm=on_confirm,
    ).root
