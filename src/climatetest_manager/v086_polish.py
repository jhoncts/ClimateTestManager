"""Refinamentos visuais da v0.8.6 após validação manual.

O formulário de cadastro passa a ter uma hierarquia semântica: identificação e
informações complementares formam a coluna de contexto, enquanto toda a
configuração térmica fica na coluna operacional. O item 26.9 aparece como uma
subseção compacta e legível, sem criar um cartão horizontal desproporcional.
"""

from __future__ import annotations

from contextlib import suppress

import flet as ft

from climatetest_manager import production_app, v084_stability, v086_runtime
from climatetest_manager.ui.theme import AppColors
from climatetest_manager.ui.views.final_new_test import FinalNewTestView

_ORIGINAL_COLD_CHANGE = v086_runtime.V086NewTestView._on_cold_change


def _walk(control: ft.Control):
    yield control
    child = getattr(control, "content", None)
    if isinstance(child, ft.Control):
        yield from _walk(child)
    children = getattr(control, "controls", None)
    if isinstance(children, list):
        for item in children:
            if isinstance(item, ft.Control):
                yield from _walk(item)


def _improve_legibility(control: ft.Control) -> None:
    """Eleva somente os textos auxiliares minúsculos do cadastro."""

    for item in _walk(control):
        if not isinstance(item, ft.Text):
            continue
        size = item.size
        if not isinstance(size, (int, float)):
            continue
        if size <= 8:
            item.size = 9.5
        elif size < 10:
            item.size = 10


def _compact_notes_panel(self: v086_runtime.V086NewTestView) -> ft.Container:
    """Mantém observações próximas da identificação em vez de ocupar a tela toda."""

    self.notes.height = 82
    self.notes.min_lines = 2
    self.notes.max_lines = 3
    self.notes.label_style = ft.TextStyle(size=11)
    return ft.Container(
        bgcolor=AppColors.SURFACE,
        border=ft.Border.all(1, AppColors.DIVIDER),
        border_radius=14,
        padding=12,
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    spacing=9,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=32,
                            height=32,
                            border_radius=9,
                            bgcolor=AppColors.PRIMARY_LIGHT,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                ft.Icons.CHAT_BUBBLE_OUTLINE,
                                size=17,
                                color=AppColors.PRIMARY,
                            ),
                        ),
                        ft.Column(
                            expand=True,
                            spacing=1,
                            controls=[
                                ft.Text(
                                    "Informações complementares",
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    "Observações opcionais sobre o ensaio.",
                                    size=10,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                    ],
                ),
                self.notes,
                ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    controls=[self._notes_count],
                ),
            ],
        ),
    )


def _integrated_thermal_panel(self: v086_runtime.V086NewTestView) -> ft.Container:
    """Integra o item 26.9 ao contexto térmico com hierarquia visual correta."""

    panel = FinalNewTestView._thermal_panel(self)
    content = panel.content
    if not isinstance(content, ft.Column):
        return panel

    # O título normativo é a informação principal. O switch vira apenas a ação.
    self.cold_planned.label = "Realizar ensaio"
    self.minimum_ambient_service_temperature.height = 46
    self.minimum_ambient_service_temperature.dense = True
    self.minimum_ambient_service_temperature.label_style = ft.TextStyle(size=11)
    self.minimum_ambient_service_temperature.hint_style = ft.TextStyle(size=10)
    self._cold_preview.size = 11
    self._cold_preview.weight = ft.FontWeight.W_500

    self._cold_fields.content = ft.Column(
        spacing=7,
        controls=[
            ft.ResponsiveRow(
                spacing=10,
                run_spacing=7,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        col={"xs": 12, "md": 6},
                        content=self.minimum_ambient_service_temperature,
                    ),
                    ft.Container(
                        col={"xs": 12, "md": 6},
                        padding=ft.Padding.symmetric(horizontal=2, vertical=1),
                        content=self._cold_preview,
                    ),
                ],
            ),
            ft.Text(
                "Após o calor: acondicionamento de 24 a 72 h. "
                "No frio: permanência de 24 a 26 h.",
                size=10,
                color=AppColors.TEXT_SECONDARY,
            ),
        ],
    )

    cold_section = ft.Container(
        bgcolor=AppColors.PAGE_BACKGROUND,
        border=ft.Border.all(1, AppColors.DIVIDER),
        border_radius=12,
        padding=10,
        content=ft.Column(
            spacing=7,
            controls=[
                ft.Row(
                    spacing=9,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=34,
                            height=34,
                            border_radius=10,
                            bgcolor=AppColors.PRIMARY_LIGHT,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                ft.Icons.AC_UNIT,
                                size=18,
                                color=AppColors.PRIMARY,
                            ),
                        ),
                        ft.Column(
                            expand=True,
                            spacing=1,
                            controls=[
                                ft.Text(
                                    "26.9 - Resistência térmica ao frio",
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    "Etapa opcional após o acondicionamento pós-calor.",
                                    size=10,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                        self.cold_planned,
                    ],
                ),
                self._cold_fields,
            ],
        ),
    )
    self._cold_panel_control = cold_section

    # Limita a largura visual do bloco 26.9 dentro do card térmico. Em telas
    # menores ele volta a ocupar a largura disponível automaticamente.
    content.controls.extend(
        [
            ft.Divider(height=1, color=AppColors.DIVIDER),
            ft.ResponsiveRow(
                spacing=0,
                run_spacing=0,
                controls=[
                    ft.Container(
                        col={"xs": 12, "lg": 9},
                        content=cold_section,
                    )
                ],
            ),
        ]
    )

    # As alternativas tinham textos de 8/9 px e ficavam difíceis de ler em
    # notebooks com escala do Windows acima de 100%.
    option_a = getattr(self, "_option_card_a", None)
    option_b = getattr(self, "_option_card_b", None)
    for option_card in (option_a, option_b):
        if isinstance(option_card, ft.Container):
            option_card.height = 64
    self.option_panel.height = 116
    _improve_legibility(panel)
    return panel


def _build_semantic(self: v086_runtime.V086NewTestView) -> ft.Column:
    """Organiza o cadastro por significado em vez de cards horizontais soltos."""

    self._prepare_controls()

    identity_panel = self._identity_panel()
    thermal_panel = self._thermal_panel()
    notes_panel = _compact_notes_panel(self)

    # Sem alturas artificiais: cada coluna cresce conforme o seu conteúdo. Isso
    # elimina o desalinhamento causado pelo 26.9 aumentar só o card da direita.
    identity_panel.height = None
    identity_panel.expand = None
    thermal_panel.height = None
    thermal_panel.expand = None
    self._identity_panel_control = identity_panel
    self._thermal_panel_control = thermal_panel

    workspace = ft.ResponsiveRow(
        spacing=12,
        run_spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[
            ft.Container(
                col={"xs": 12, "lg": 5},
                content=ft.Column(
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[identity_panel, notes_panel],
                ),
            ),
            ft.Container(
                col={"xs": 12, "lg": 7},
                content=thermal_panel,
            ),
        ],
    )

    header = ft.Row(
        wrap=False,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Column(
                expand=True,
                spacing=2,
                controls=[
                    ft.Text(
                        "Editar ensaio" if self._details else "Novo ensaio",
                        size=27,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        "Identifique a amostra e configure as condições do ensaio.",
                        size=11,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                ],
            ),
            ft.Row(
                spacing=7,
                controls=[
                    ft.Button(
                        content="Cancelar",
                        icon=ft.Icons.CLOSE,
                        on_click=lambda _event: self._on_cancel(),
                    ),
                    self.save_button,
                ],
            ),
        ],
    )

    controls: list[ft.Control] = [header, self.error_banner, workspace]
    if self._details:
        controls.append(
            ft.Container(
                bgcolor=AppColors.SURFACE,
                border=ft.Border.all(1, AppColors.DIVIDER),
                border_radius=14,
                padding=12,
                content=self.change_reason_selector.control,
            )
        )
    controls.extend([self.result_panel, ft.Container(height=8)])

    root = ft.Column(
        key=f"v086-new-test-{id(self)}",
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=controls,
    )
    _improve_legibility(workspace)
    return root


def _sync_semantic_layout(self: v086_runtime.V086NewTestView) -> None:
    """Mantém os cards livres de alturas fixas durante trocas de modo."""

    mode = self.mode_group.value
    if hasattr(self, "_mode_selector_box") and hasattr(self, "_thermal_input_box"):
        if mode == "direct_configuration":
            self._mode_selector_box.col = {"xs": 12, "sm": 4}
            self._thermal_input_box.col = {"xs": 12, "sm": 8}
        else:
            self._mode_selector_box.col = {"xs": 12, "sm": 5}
            self._thermal_input_box.col = {"xs": 12, "sm": 7}

    for panel in (
        getattr(self, "_identity_panel_control", None),
        getattr(self, "_thermal_panel_control", None),
    ):
        if isinstance(panel, ft.Container):
            panel.height = None
            with suppress(RuntimeError):
                panel.update()


def _cold_change_semantic(self: v086_runtime.V086NewTestView, event=None) -> None:
    _ORIGINAL_COLD_CHANGE(self, event)
    _sync_semantic_layout(self)


def install() -> None:
    if getattr(production_app, "_v086_polish_installed", False):
        return

    # A lateral continua visível durante a animação, mas com duração curta para
    # não parecer pesada em notebooks com WebView2.
    v084_stability.SIDEBAR_ANIMATION_SECONDS = 0.14
    v086_runtime.V086NewTestView._thermal_panel = _integrated_thermal_panel
    v086_runtime.V086NewTestView._build = _build_semantic
    v086_runtime.V086NewTestView._sync_top_card_height = _sync_semantic_layout
    v086_runtime.V086NewTestView._on_cold_change = _cold_change_semantic
    production_app._v086_polish_installed = True
