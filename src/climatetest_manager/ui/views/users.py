"""Administração local de usuários e perfis."""

from collections.abc import Callable

import flet as ft

from climatetest_manager.services.auth import (
    UserRegistrationCommand,
    UserSummary,
    UserUpdateCommand,
)
from climatetest_manager.ui.components import (
    dialog_actions,
    dialog_banner,
    styled_dialog,
    user_avatar,
)
from climatetest_manager.ui.formatters import format_datetime
from climatetest_manager.ui.theme import AppColors


class UsersView:
    """Lista contas e oferece criação, correção, ativação e redefinição de senha."""

    def __init__(
        self,
        users: list[UserSummary],
        *,
        current_user: UserSummary,
        on_create: Callable[[UserRegistrationCommand], str | None],
        on_update: Callable[[int, UserUpdateCommand], str | None],
        on_reset_password: Callable[[int, str, str], str | None],
    ) -> None:
        self._users = users
        self._current_user = current_user
        self._on_create = on_create
        self._on_update = on_update
        self._on_reset_password = on_reset_password
        self.root = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=18,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    wrap=True,
                    run_spacing=10,
                    controls=[
                        ft.Column(
                            spacing=3,
                            controls=[
                                ft.Text(
                                    "Usuários",
                                    size=28,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    "Contas locais autorizadas a operar o sistema.",
                                    size=14,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                        ft.Button(
                            content="Novo usuário",
                            icon=ft.Icons.PERSON_ADD,
                            bgcolor=AppColors.PRIMARY,
                            color=AppColors.WHITE,
                            on_click=lambda _event: self._show_create_dialog(),
                        ),
                    ],
                ),
                ft.Container(
                    border_radius=12,
                    bgcolor=AppColors.INFO_LIGHT,
                    padding=14,
                    content=ft.Text(
                        "Administradores gerenciam contas e também operam ensaios. "
                        "Operadores acessam todas as funções técnicas, mas não alteram usuários.",
                        size=12,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                ),
                *[self._user_card(user) for user in users],
            ],
        )

    def _user_card(self, user: UserSummary) -> ft.Container:
        status_color = AppColors.PRIMARY if user.is_active else AppColors.DANGER
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border_radius=15,
            padding=18,
            content=ft.ResponsiveRow(
                spacing=14,
                run_spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        col={"xs": 12, "md": 7, "lg": 8},
                        content=ft.Row(
                            spacing=14,
                            controls=[
                                user_avatar(user, size=42),
                                ft.Column(
                                    expand=True,
                                    spacing=3,
                                    controls=[
                                        ft.Text(
                                            user.full_name,
                                            size=15,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            f"@{user.username} • {user.email}",
                                            size=12,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                        ft.Text(
                                            "Último acesso: " + format_datetime(user.last_login_at),
                                            size=11,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ),
                    ft.Container(
                        col={"xs": 12, "md": 5, "lg": 4},
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.END,
                            wrap=True,
                            run_spacing=6,
                            controls=[
                                ft.Container(
                                    border_radius=16,
                                    bgcolor=AppColors.PRIMARY_LIGHT,
                                    padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                                    content=ft.Text(
                                        user.role_label,
                                        size=11,
                                        weight=ft.FontWeight.BOLD,
                                        color=AppColors.PRIMARY,
                                    ),
                                ),
                                ft.Text(
                                    "Ativo" if user.is_active else "Desativado",
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                    color=status_color,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    tooltip="Editar usuário",
                                    on_click=lambda _event, selected=user: self._show_edit_dialog(
                                        selected
                                    ),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.PASSWORD,
                                    tooltip="Redefinir senha",
                                    on_click=lambda _event, selected=user: self._show_reset_dialog(
                                        selected
                                    ),
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )

    def _identity_fields(
        self,
        user: UserSummary | None = None,
    ) -> tuple[ft.TextField, ft.TextField, ft.TextField, ft.TextField]:
        first_name = ft.TextField(
            label="Nome",
            value=user.first_name if user else "",
            border_radius=10,
            max_length=80,
            counter="",
        )
        last_name = ft.TextField(
            label="Sobrenome",
            value=user.last_name if user else "",
            border_radius=10,
            max_length=120,
            counter="",
        )
        username = ft.TextField(
            label="Nome de usuário",
            value=user.username if user else "",
            border_radius=10,
            max_length=32,
            counter="",
        )
        email = ft.TextField(
            label="E-mail",
            value=user.email if user else "",
            keyboard_type=ft.KeyboardType.EMAIL,
            border_radius=10,
            max_length=254,
            counter="",
        )
        return first_name, last_name, username, email

    @staticmethod
    def _identity_grid(
        first_name: ft.TextField,
        last_name: ft.TextField,
        username: ft.TextField,
        email: ft.TextField,
        role: ft.Dropdown,
    ) -> ft.ResponsiveRow:
        """Organiza campos em duas colunas e os empilha em janelas estreitas."""

        return ft.ResponsiveRow(
            spacing=14,
            run_spacing=12,
            controls=[
                ft.Container(col={"xs": 12, "sm": 6}, content=first_name),
                ft.Container(col={"xs": 12, "sm": 6}, content=last_name),
                ft.Container(col={"xs": 12, "sm": 7}, content=username),
                ft.Container(col={"xs": 12, "sm": 5}, content=role),
                ft.Container(col={"xs": 12}, content=email),
            ],
        )

    @staticmethod
    def _dialog_actions(
        *,
        page: ft.Page,
        primary_label: str,
        on_confirm: Callable[[object | None], None],
    ) -> list[ft.Control]:
        return dialog_actions(
            page=page,
            primary_label=primary_label,
            on_confirm=on_confirm,
        )

    def _show_create_dialog(self) -> None:
        first_name, last_name, username, email = self._identity_fields()
        role = ft.Dropdown(
            label="Perfil",
            value="operator",
            options=[
                ft.DropdownOption(key="operator", text="Operador"),
                ft.DropdownOption(key="admin", text="Administrador"),
            ],
        )
        password = ft.TextField(
            label="Senha",
            password=True,
            can_reveal_password=True,
            max_length=128,
            counter="",
        )
        confirmation = ft.TextField(
            label="Confirmar senha",
            password=True,
            can_reveal_password=True,
            max_length=128,
            counter="",
        )
        error_text = ft.Text("", size=11, color=AppColors.DANGER)
        page = self.root.page

        def confirm(_event: object | None = None) -> None:
            command = UserRegistrationCommand(
                username=username.value,
                email=email.value,
                first_name=first_name.value,
                last_name=last_name.value,
                password=password.value,
                password_confirmation=confirmation.value,
                role=role.value or "operator",
            )
            error = self._on_create(command)
            if error:
                error_text.value = error
                error_text.update()
                return
            page.pop_dialog()

        page.show_dialog(
            styled_dialog(
                title="Cadastrar usuário",
                subtitle="Nova conta autorizada para acessar o sistema",
                icon=ft.Icons.PERSON_ADD_ALT_1,
                scrollable=True,
                content=ft.Column(
                    tight=True,
                    width=620,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=16,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        dialog_banner(
                            "Somente administradores cadastram contas. Não existe autocadastro.",
                            icon=ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
                        ),
                        self._identity_grid(
                            first_name,
                            last_name,
                            username,
                            email,
                            role,
                        ),
                        ft.Divider(height=1, color=AppColors.DIVIDER),
                        ft.ResponsiveRow(
                            spacing=14,
                            run_spacing=12,
                            controls=[
                                ft.Container(
                                    col={"xs": 12, "sm": 6},
                                    content=password,
                                ),
                                ft.Container(
                                    col={"xs": 12, "sm": 6},
                                    content=confirmation,
                                ),
                            ],
                        ),
                        ft.Text(
                            "A senha deve ter no mínimo 8 caracteres, uma letra e um número.",
                            size=11,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        error_text,
                    ],
                ),
                actions=self._dialog_actions(
                    page=page,
                    primary_label="Cadastrar usuário",
                    on_confirm=confirm,
                ),
            )
        )

    def _show_edit_dialog(self, user: UserSummary) -> None:
        first_name, last_name, username, email = self._identity_fields(user)
        role = ft.Dropdown(
            label="Perfil",
            value=user.role,
            options=[
                ft.DropdownOption(key="operator", text="Operador"),
                ft.DropdownOption(key="admin", text="Administrador"),
            ],
        )
        active = ft.Switch(
            label="Conta ativa",
            value=user.is_active,
            disabled=user.id == self._current_user.id,
        )
        error_text = ft.Text("", size=11, color=AppColors.DANGER)
        page = self.root.page

        def confirm(_event: object | None = None) -> None:
            command = UserUpdateCommand(
                username=username.value,
                email=email.value,
                first_name=first_name.value,
                last_name=last_name.value,
                role=role.value or "operator",
                is_active=bool(active.value),
            )
            error = self._on_update(user.id, command)
            if error:
                error_text.value = error
                error_text.update()
                return
            page.pop_dialog()

        page.show_dialog(
            styled_dialog(
                title=f"Editar @{user.username}",
                subtitle="Dados de acesso, perfil e situação da conta",
                icon=ft.Icons.MANAGE_ACCOUNTS_OUTLINED,
                scrollable=True,
                content=ft.Column(
                    tight=True,
                    width=620,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=16,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        self._identity_grid(
                            first_name,
                            last_name,
                            username,
                            email,
                            role,
                        ),
                        ft.Container(
                            border_radius=12,
                            bgcolor=AppColors.PAGE_BACKGROUND,
                            border=ft.Border.all(1, AppColors.DIVIDER),
                            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Column(
                                        spacing=1,
                                        controls=[
                                            ft.Text(
                                                "Acesso ao sistema",
                                                size=12,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                            ft.Text(
                                                (
                                                    "A própria conta do administrador "
                                                    "não pode ser desativada."
                                                    if user.id == self._current_user.id
                                                    else "Desative para bloquear novos acessos."
                                                ),
                                                size=10,
                                                color=AppColors.TEXT_SECONDARY,
                                            ),
                                        ],
                                    ),
                                    active,
                                ],
                            ),
                        ),
                        error_text,
                    ],
                ),
                actions=self._dialog_actions(
                    page=page,
                    primary_label="Salvar alterações",
                    on_confirm=confirm,
                ),
            )
        )

    def _show_reset_dialog(self, user: UserSummary) -> None:
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

        def confirm(_event: object | None = None) -> None:
            error = self._on_reset_password(
                user.id,
                password.value,
                confirmation.value,
            )
            if error:
                error_text.value = error
                error_text.update()
                return
            page.pop_dialog()

        page.show_dialog(
            styled_dialog(
                title=f"Redefinir senha de @{user.username}",
                subtitle="As sessões existentes serão encerradas",
                icon=ft.Icons.LOCK_RESET,
                danger=True,
                content=ft.Column(
                    tight=True,
                    width=440,
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        dialog_banner(
                            "O usuário precisará entrar novamente com a nova senha.",
                            icon=ft.Icons.LOGOUT,
                            warning=True,
                        ),
                        password,
                        confirmation,
                        error_text,
                    ],
                ),
                actions=dialog_actions(
                    page=page,
                    primary_label="Redefinir senha",
                    primary_icon=ft.Icons.LOCK_RESET,
                    on_confirm=confirm,
                    danger=True,
                ),
            )
        )


def build_users_view(
    users: list[UserSummary],
    *,
    current_user: UserSummary,
    on_create: Callable[[UserRegistrationCommand], str | None],
    on_update: Callable[[int, UserUpdateCommand], str | None],
    on_reset_password: Callable[[int, str, str], str | None],
) -> ft.Column:
    return UsersView(
        users,
        current_user=current_user,
        on_create=on_create,
        on_update=on_update,
        on_reset_password=on_reset_password,
    ).root
