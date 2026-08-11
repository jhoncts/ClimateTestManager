"""Visualização original e compacta das condições da Tabela 17.

A regra de cálculo continua em ``domain.climate_rules``. Este módulo apenas apresenta as
faixas e alternativas de forma visual, sem depender de captura de tela ou marca d'água.
"""

from __future__ import annotations

from dataclasses import dataclass

import flet as ft

from climatetest_manager.ui.theme import AppColors


@dataclass(frozen=True, slots=True)
class _RuleRow:
    group: str
    epls: str
    ts_band: str
    option_a: str
    option_b: str
    rule_a: str
    rule_b: str | None


_ROWS = (
    _RuleRow(
        group="G1",
        epls="Ga • Gb • Da • Db • Ma • Mb",
        ts_band="Ts ≤ 70 °C",
        option_a="672 h • 90 ± 5% UR • Ts + 20 ± 2 K (mín. 80 °C)",
        option_b="—",
        rule_a="G1-LOW-A",
        rule_b=None,
    ),
    _RuleRow(
        group="G1",
        epls="Ga • Gb • Da • Db • Ma • Mb",
        ts_band="70 °C < Ts < 75 °C",
        option_a="672 h • 90 ± 5% UR • Ts + 20 ± 2 K",
        option_b="504 h • 90 ± 5% UR • 90 ± 2 °C → 336 h seco • Ts + 20 ± 2 K",
        rule_a="G1-MID-A",
        rule_b="G1-MID-B",
    ),
    _RuleRow(
        group="G1",
        epls="Ga • Gb • Da • Db • Ma • Mb",
        ts_band="Ts ≥ 75 °C",
        option_a="336 h • 90 ± 5% UR • 95 ± 2 °C → 336 h seco • Ts + 20 ± 2 K",
        option_b="504 h • 90 ± 5% UR • 90 ± 2 °C → 336 h seco • Ts + 20 ± 2 K",
        rule_a="G1-HIGH-A",
        rule_b="G1-HIGH-B",
    ),
    _RuleRow(
        group="G2",
        epls="Gc • Dc",
        ts_band="Ts ≤ 80 °C",
        option_a="672 h • 90 ± 5% UR • Ts + 10 ± 2 K",
        option_b="—",
        rule_a="G2-LOW-A",
        rule_b=None,
    ),
    _RuleRow(
        group="G2",
        epls="Gc • Dc",
        ts_band="80 °C < Ts ≤ 85 °C",
        option_a="672 h • 90 ± 5% UR • Ts + 10 ± 2 K",
        option_b="336 h • 90 ± 5% UR • 90 ± 2 °C → 336 h seco • Ts + 10 ± 2 K",
        rule_a="G2-MID-A",
        rule_b="G2-MID-B",
    ),
    _RuleRow(
        group="G2",
        epls="Gc • Dc",
        ts_band="Ts > 85 °C",
        option_a="336 h • 90 ± 5% UR • 95 ± 2 °C → 336 h seco • Ts + 10 ± 2 K",
        option_b="504 h • 90 ± 5% UR • 90 ± 2 °C → 336 h seco • Ts + 10 ± 2 K",
        rule_a="G2-HIGH-A",
        rule_b="G2-HIGH-B",
    ),
)


def _cell(
    text: str,
    *,
    width: int | None = None,
    active: bool = False,
    header: bool = False,
    align: ft.Alignment = ft.Alignment.CENTER_LEFT,
) -> ft.Container:
    background = (
        AppColors.PRIMARY_LIGHT
        if active
        else AppColors.PAGE_BACKGROUND
        if header
        else AppColors.SURFACE
    )
    border_color = AppColors.PRIMARY if active else AppColors.DIVIDER
    return ft.Container(
        width=width,
        height=58 if not header else 42,
        padding=ft.Padding.symmetric(horizontal=10, vertical=8),
        border=ft.Border.all(2 if active else 1, border_color),
        bgcolor=background,
        alignment=align,
        animate=ft.Animation(160, ft.AnimationCurve.EASE_OUT_CUBIC),
        shadow=(
            ft.BoxShadow(
                blur_radius=15,
                spread_radius=0,
                color=AppColors.ACCENT_GLOW,
                offset=ft.Offset(0, 0),
            )
            if active
            else None
        ),
        content=ft.Row(
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                *(
                    [ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color=AppColors.PRIMARY)]
                    if active
                    else []
                ),
                ft.Text(
                    text,
                    expand=True,
                    size=10 if not header else 11,
                    weight=ft.FontWeight.BOLD if header or active else ft.FontWeight.NORMAL,
                    color=AppColors.TEXT_PRIMARY,
                    no_wrap=False,
                ),
            ],
        ),
    )


def _row(rule: _RuleRow, active_rule_id: str | None) -> ft.Row:
    return ft.Row(
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            _cell(rule.epls, width=150),
            _cell(rule.ts_band, width=155),
            ft.Container(
                expand=True,
                content=_cell(rule.option_a, active=active_rule_id == rule.rule_a),
            ),
            ft.Container(
                expand=True,
                content=_cell(
                    rule.option_b,
                    active=bool(rule.rule_b and active_rule_id == rule.rule_b),
                ),
            ),
        ],
    )


def build_table17_preview(
    active_rule_id: str | None,
    *,
    compact: bool = False,
    show_caption: bool = True,
) -> ft.Control:
    """Monta a tabela e destaca exatamente a regra utilizada pelo motor normativo."""

    if active_rule_id == "DIRECT-CONFIGURATION":
        return ft.Container(
            border_radius=14,
            bgcolor=AppColors.INFO_LIGHT,
            border=ft.Border.all(1, AppColors.DIVIDER),
            padding=14,
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Icon(ft.Icons.TUNE, color=AppColors.INFO),
                    ft.Text(
                        "Condição personalizada: a Tabela 17 não é destacada porque os valores "
                        "foram informados diretamente pelo plano/cliente.",
                        expand=True,
                        size=11,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                ],
            ),
        )

    table = ft.Column(
        spacing=0,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            ft.Row(
                spacing=0,
                controls=[
                    _cell("EPL", width=150, header=True, align=ft.Alignment.CENTER),
                    _cell("Temperatura de serviço Ts", width=155, header=True),
                    ft.Container(expand=True, content=_cell("Alternativa A", header=True)),
                    ft.Container(expand=True, content=_cell("Alternativa B", header=True)),
                ],
            ),
            *[_row(rule, active_rule_id) for rule in _ROWS],
        ],
    )
    table_surface = ft.Container(
        border_radius=14,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        border=ft.Border.all(1, AppColors.DIVIDER),
        content=table,
    )

    body: ft.Control
    if compact:
        body = ft.Column(
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Text(
                    "Tabela 17 • referência visual",
                    size=13,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
                ft.Text(
                    "A borda de destaque acompanha automaticamente EPL, Ts e alternativa.",
                    size=10,
                    color=AppColors.TEXT_SECONDARY,
                ),
                ft.Row(
                    scroll=ft.ScrollMode.AUTO,
                    controls=[ft.Container(width=840, content=table_surface)],
                ),
            ],
        )
    else:
        body = ft.Column(
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    wrap=True,
                    run_spacing=6,
                    controls=[
                        ft.Column(
                            spacing=2,
                            controls=[
                                ft.Text(
                                    "Tabela 17 — resistência térmica",
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    "Resumo visual gerado pelo ClimateTest Manager a partir da "
                                    "regra cadastrada para ABNT NBR IEC 60079-0:2020.",
                                    size=10,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                        ft.Container(
                            border_radius=20,
                            bgcolor=AppColors.PRIMARY_LIGHT,
                            padding=ft.Padding.symmetric(horizontal=11, vertical=6),
                            content=ft.Text(
                                "Condição aplicada destacada",
                                size=10,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.PRIMARY,
                            ),
                        ),
                    ],
                ),
                ft.Row(
                    scroll=ft.ScrollMode.AUTO,
                    controls=[ft.Container(width=920, content=table_surface)],
                ),
            ],
        )

    controls: list[ft.Control] = [body]
    if show_caption:
        controls.append(
            ft.Text(
                "Visualização de apoio. A norma controlada e o plano de ensaio continuam sendo "
                "as referências formais para a execução e o relatório.",
                size=9,
                color=AppColors.TEXT_SECONDARY,
            )
        )
    return ft.Container(
        border_radius=16,
        bgcolor=AppColors.GLASS_SURFACE,
        border=ft.Border.all(1, AppColors.GLASS_BORDER),
        padding=16,
        content=ft.Column(
            spacing=9,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=controls,
        ),
    )
