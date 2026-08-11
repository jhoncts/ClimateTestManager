"""Componentes compartilhados para diálogos e justificativas auditáveis."""

from collections.abc import Callable, Sequence
from contextlib import suppress

import flet as ft

from climatetest_manager.domain.audit import MAX_REASON_LENGTH
from climatetest_manager.ui.theme import AppColors

OTHER_REASON = "Outros"


def _noop_value_event(_event: object | None = None) -> None:
    """Faz o cliente enviar o valor alterado ao servidor sem executar lógica adicional."""


def _enable_remote_value_sync(control: ft.Control) -> None:
    """Liga eventos mínimos em inputs que seriam lidos apenas no botão de confirmação.

    Em uma sessão Flet remota, um campo sem evento pode permanecer somente no cliente até que
    outro controle seja acionado. Isso fazia o servidor enxergar strings antigas/vazias mesmo
    quando o usuário via o texto digitado na tela. Percorrer o conteúdo dos diálogos elimina
    essa diferença sem alterar a regra de negócio de cada formulário.
    """

    if isinstance(control, ft.TextField) and control.on_change is None:
        control.on_change = _noop_value_event
    elif isinstance(control, ft.Switch) and control.on_change is None:
        control.on_change = _noop_value_event
    elif isinstance(control, ft.Checkbox) and control.on_change is None:
        control.on_change = _noop_value_event
    elif isinstance(control, ft.Dropdown) and control.on_select is None:
        control.on_select = _noop_value_event

    child = getattr(control, "content", None)
    if isinstance(child, ft.Control):
        _enable_remote_value_sync(child)
    children = getattr(control, "controls", None)
    if isinstance(children, list):
        for item in children:
            if isinstance(item, ft.Control):
                _enable_remote_value_sync(item)


def dialog_header(
    title: str,
    subtitle: str,
    *,
    icon: ft.IconData,
    danger: bool = False,
) -> ft.Row:
    """Cria um cabeçalho consistente, legível e preparado para títulos longos."""

    accent = AppColors.DANGER if danger else AppColors.PRIMARY
    background = AppColors.DANGER_LIGHT if danger else AppColors.PRIMARY_LIGHT
    return ft.Row(
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(
                width=44,
                height=44,
                border_radius=14,
                bgcolor=background,
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(icon, color=accent, size=23),
            ),
            ft.Column(
                expand=True,
                spacing=2,
                controls=[
                    ft.Text(
                        title,
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        subtitle,
                        size=11,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                ],
            ),
        ],
    )


def dialog_banner(
    message: str,
    *,
    icon: ft.IconData = ft.Icons.INFO_OUTLINE,
    danger: bool = False,
    warning: bool = False,
) -> ft.Container:
    """Apresenta uma orientação curta sem competir com o conteúdo do diálogo."""

    if danger:
        color, background = AppColors.DANGER, AppColors.DANGER_LIGHT
    elif warning:
        color, background = AppColors.WARNING, AppColors.WARNING_LIGHT
    else:
        color, background = AppColors.INFO, AppColors.INFO_LIGHT
    return ft.Container(
        border_radius=12,
        bgcolor=background,
        padding=12,
        content=ft.Row(
            spacing=9,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Icon(icon, color=color, size=19),
                ft.Text(
                    message,
                    expand=True,
                    size=11,
                    color=AppColors.TEXT_PRIMARY,
                ),
            ],
        ),
    )


def dialog_actions(
    *,
    page: ft.Page,
    primary_label: str,
    on_confirm: Callable[[object | None], None],
    primary_icon: ft.IconData = ft.Icons.CHECK,
    danger: bool = False,
    cancel_label: str = "Voltar",
) -> list[ft.Control]:
    """Padroniza ações com um botão principal visualmente inequívoco."""

    accent = AppColors.DANGER if danger else AppColors.PRIMARY
    return [
        ft.TextButton(
            content=cancel_label,
            on_click=lambda _event: page.pop_dialog(),
        ),
        ft.Button(
            content=primary_label,
            icon=primary_icon,
            bgcolor=accent,
            color=AppColors.WHITE,
            on_click=on_confirm,
        ),
    ]


def styled_dialog(
    *,
    title: str,
    subtitle: str,
    icon: ft.IconData,
    content: ft.Control,
    actions: list[ft.Control],
    danger: bool = False,
    scrollable: bool = False,
) -> ft.AlertDialog:
    """Monta a superfície visual comum de todos os diálogos da aplicação."""

    _enable_remote_value_sync(content)
    return ft.AlertDialog(
        modal=True,
        scrollable=scrollable,
        bgcolor=AppColors.SURFACE,
        shape=ft.RoundedRectangleBorder(radius=22),
        inset_padding=20,
        title_padding=ft.Padding.only(left=24, top=22, right=24, bottom=10),
        content_padding=ft.Padding.symmetric(horizontal=24, vertical=8),
        actions_padding=ft.Padding.only(left=24, top=12, right=24, bottom=20),
        title=dialog_header(title, subtitle, icon=icon, danger=danger),
        content=content,
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.END,
    )


class ReasonSelector:
    """Combina motivos rápidos com um campo limitado para a opção “Outros”."""

    def __init__(
        self,
        options: Sequence[str],
        *,
        label: str = "Motivo *",
        other_hint: str = "Descreva o motivo brevemente",
    ) -> None:
        unique_options = tuple(dict.fromkeys((*options, OTHER_REASON)))
        self.dropdown = ft.Dropdown(
            label=label,
            hint_text="Selecione uma opção",
            options=[ft.DropdownOption(key=option, text=option) for option in unique_options],
            border_radius=10,
            border_color=AppColors.DIVIDER,
            focused_border_color=AppColors.PRIMARY,
            bgcolor=AppColors.SURFACE,
            on_select=self._on_select,
        )
        self.other = ft.TextField(
            label="Outro motivo *",
            hint_text=other_hint,
            max_length=MAX_REASON_LENGTH,
            multiline=True,
            min_lines=2,
            max_lines=3,
            border_radius=10,
            border_color=AppColors.DIVIDER,
            focused_border_color=AppColors.PRIMARY,
            bgcolor=AppColors.SURFACE,
            visible=False,
            on_change=_noop_value_event,
        )
        self.other_guidance = ft.Text(
            f"Descreva brevemente, em até {MAX_REASON_LENGTH} caracteres.",
            size=10,
            color=AppColors.TEXT_SECONDARY,
            visible=False,
        )
        self.control = ft.Column(
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[self.dropdown, self.other, self.other_guidance],
        )

    def _on_select(self, _event: object | None = None) -> None:
        self.other.visible = self.dropdown.value == OTHER_REASON
        self.other_guidance.visible = self.other.visible
        self.dropdown.error_text = None
        if not self.other.visible:
            self.other.value = ""
            self.other.error = None
        with suppress(RuntimeError):
            self.control.update()

    def value(self) -> str:
        """Retorna a justificativa final ou uma string vazia quando incompleta."""

        selected = (self.dropdown.value or "").strip()
        if selected != OTHER_REASON:
            return selected
        return self.other.value.strip()

    def validate(self, *, message: str = "Selecione o motivo.") -> bool:
        """Marca somente o campo incompleto, sem redesenhar a tela inteira."""

        selected = (self.dropdown.value or "").strip()
        self.dropdown.error_text = None
        self.other.error = None
        if not selected:
            self.dropdown.error_text = message
            with suppress(RuntimeError):
                self.dropdown.update()
            return False
        if selected == OTHER_REASON and not self.other.value.strip():
            self.other.error = "Descreva o motivo."
            with suppress(RuntimeError):
                self.other.update()
            return False
        return True
