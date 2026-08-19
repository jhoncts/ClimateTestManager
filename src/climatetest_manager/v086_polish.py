"""Refinamentos visuais do beta v0.8.6 após validação manual.

O planejamento do frio passa a fazer parte do próprio cartão de configuração
térmica e as transições evitam deslocamento da superfície central.
"""

from __future__ import annotations

import flet as ft

from climatetest_manager import production_app, v084_stability, v086_runtime
from climatetest_manager.ui.theme import AppColors
from climatetest_manager.ui.views.final_new_test import FinalNewTestView


def _integrated_thermal_panel(self: v086_runtime.V086NewTestView) -> ft.Container:
    """Integra o pós-calor à configuração térmica sem criar um cartão alto isolado."""

    panel = FinalNewTestView._thermal_panel(self)
    content = panel.content
    if not isinstance(content, ft.Column):
        return panel

    self.cold_planned.label = "Realizar frio — 26.9"
    self._cold_fields.content = ft.ResponsiveRow(
        spacing=10,
        run_spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(
                col={"xs": 12, "md": 5},
                content=self.minimum_ambient_service_temperature,
            ),
            ft.Container(
                col={"xs": 12, "md": 7},
                padding=ft.Padding.symmetric(horizontal=4, vertical=2),
                content=ft.Column(
                    spacing=2,
                    controls=[
                        self._cold_preview,
                        ft.Text(
                            "Acondicionamento pós-calor: 24 a 72 h • Frio: 24 a 26 h.",
                            size=9,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
            ),
        ],
    )

    integrated = ft.Container(
        bgcolor=AppColors.PAGE_BACKGROUND,
        border=ft.Border.all(1, AppColors.DIVIDER),
        border_radius=11,
        padding=ft.Padding.symmetric(horizontal=10, vertical=8),
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=28,
                            height=28,
                            border_radius=8,
                            bgcolor=AppColors.PRIMARY_LIGHT,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                ft.Icons.AC_UNIT,
                                size=15,
                                color=AppColors.PRIMARY,
                            ),
                        ),
                        ft.Column(
                            expand=True,
                            spacing=0,
                            controls=[
                                ft.Text(
                                    "Após o calor",
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    "Acondicionamento obrigatório; frio opcional.",
                                    size=8,
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
    self._cold_panel_control = integrated
    content.controls.extend(
        [
            ft.Divider(height=1, color=AppColors.DIVIDER),
            integrated,
        ]
    )
    return panel


def _build_integrated(self: v086_runtime.V086NewTestView) -> ft.Column:
    """Usa a árvore normal do formulário; o pós-calor já está dentro do painel térmico."""

    return FinalNewTestView._build(self)


def install() -> None:
    if getattr(production_app, "_v086_polish_installed", False):
        return

    # Menor duração reduz a sensação de travamento no WebView2, mantendo a
    # animação lateral perceptível.
    v084_stability.SIDEBAR_ANIMATION_SECONDS = 0.16
    v086_runtime.V086NewTestView._thermal_panel = _integrated_thermal_panel
    v086_runtime.V086NewTestView._build = _build_integrated
    production_app._v086_polish_installed = True
