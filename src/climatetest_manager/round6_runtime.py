"""Rodada 6: refinamento visual sobre a base R5 já validada no Windows.

A R6 não troca a arquitetura que eliminou as telas vazias. Ela preserva uma única
rolagem nas telas críticas e atua somente em composição, interação, notificações e
registro de falhas.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress

import flet as ft

from climatetest_manager import app as legacy_app
from climatetest_manager import production_app
from climatetest_manager.config import load_email_settings
from climatetest_manager.domain.incidents import INCIDENT_REASONS, incident_reason
from climatetest_manager.round4_runtime import (
    _force_scroll_top,
    _safe_settings_builder,
    _safe_update,
    _walk,
)
from climatetest_manager.round5_runtime import StableNewTestView
from climatetest_manager.services.notifications import (
    EmailNotificationProvider,
    deliver_pending_incident_emails,
)
from climatetest_manager.ui import interaction as interaction_module
from climatetest_manager.ui import shell as shell_module
from climatetest_manager.ui.components import dialog_banner, styled_dialog
from climatetest_manager.ui.formatters import format_datetime
from climatetest_manager.ui.interaction import apply_interaction_polish as _base_interaction_polish
from climatetest_manager.ui.theme import AppColors
from climatetest_manager.ui.views import production_settings as production_settings_module

BUILD_REVISION = "R6-20260813"


def _revision_banner() -> ft.Container:
    return ft.Container(
        border_radius=10,
        bgcolor=AppColors.INFO_LIGHT,
        border=ft.Border.all(1, AppColors.DIVIDER),
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        content=ft.Row(
            spacing=8,
            controls=[
                ft.Icon(ft.Icons.VERIFIED_OUTLINED, size=16, color=AppColors.INFO),
                ft.Text(
                    f"Interface refinada {BUILD_REVISION}",
                    size=10,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_SECONDARY,
                ),
            ],
        ),
    )


def apply_interaction_polish(control: ft.Control) -> ft.Control:
    """Garante cursor de link e resposta Material inclusive em botões preenchidos."""

    _base_interaction_polish(control)
    for item in _walk(control):
        if isinstance(item, (ft.Button, ft.TextButton, ft.IconButton)):
            explicit_fill = bool(getattr(item, "bgcolor", None))
            overlay = {
                ft.ControlState.HOVERED: "#18FFFFFF" if explicit_fill else AppColors.INTERACTIVE_HOVER,
                ft.ControlState.PRESSED: "#38FFFFFF" if explicit_fill else AppColors.INTERACTIVE_PRESSED,
                ft.ControlState.FOCUSED: "#24FFFFFF" if explicit_fill else AppColors.INTERACTIVE_HOVER,
            }
            cursor = {
                ft.ControlState.DEFAULT: ft.MouseCursor.CLICK,
                ft.ControlState.HOVERED: ft.MouseCursor.CLICK,
                ft.ControlState.PRESSED: ft.MouseCursor.CLICK,
            }
            style = item.style or ft.ButtonStyle()
            item.style = style.copy(
                overlay_color=overlay,
                mouse_cursor=cursor,
                animation_duration=120,
            )
            with suppress(Exception):
                item.mouse_cursor = ft.MouseCursor.CLICK
        elif isinstance(item, ft.Container) and item.on_click is not None:
            with suppress(Exception):
                item.ink = True
                item.mouse_cursor = ft.MouseCursor.CLICK
    return control


def _navigation_surface(
    *,
    label: str,
    icon: ft.IconData,
    selected: bool,
    compact: bool,
    icon_size: int,
    on_click,
    badge_count: int = 0,
) -> ft.Container:
    """Badge interno: nunca invade a área da barra de rolagem da lateral."""

    selected_color = AppColors.PRIMARY if selected else AppColors.NAV_TEXT
    label_control = ft.Text(
        label,
        size=13,
        height=1.35,
        weight=ft.FontWeight.BOLD if selected else ft.FontWeight.W_500,
        color=selected_color,
        no_wrap=True,
        max_lines=1,
    )
    icon_control = ft.Icon(icon, size=icon_size, color=selected_color)
    badge = ft.Container(
        visible=badge_count > 0,
        width=22,
        height=20,
        padding=ft.Padding.symmetric(horizontal=5),
        border_radius=10,
        bgcolor=AppColors.DANGER,
        alignment=ft.Alignment.CENTER,
        content=ft.Text(
            str(min(badge_count, 99)),
            size=9,
            weight=ft.FontWeight.BOLD,
            color=AppColors.WHITE,
            no_wrap=True,
        ),
    )
    if compact:
        row_controls: list[ft.Control] = [icon_control]
        if badge_count:
            row_controls.append(badge)
    else:
        row_controls = [
            icon_control,
            ft.Container(expand=True, content=label_control),
        ]
        if badge_count:
            row_controls.append(badge)

    surface = ft.Container(
        height=52,
        border_radius=12,
        bgcolor=AppColors.NAV_SELECTED if selected else None,
        padding=ft.Padding.only(
            left=8 if compact else 12,
            right=8 if compact else 14,
            top=9,
            bottom=9,
        ),
        alignment=ft.Alignment.CENTER if compact else ft.Alignment.CENTER_LEFT,
        tooltip=label if compact else None,
        on_click=(lambda _event: on_click()) if on_click else None,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER if compact else ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=5 if compact else 11,
            controls=row_controls,
        ),
    )

    def on_hover(event: ft.HoverEvent) -> None:
        hovering = event.data == "true"
        if selected:
            surface.bgcolor = AppColors.NAV_SELECTED
            icon_control.color = AppColors.PRIMARY
            label_control.color = AppColors.PRIMARY
        elif hovering:
            surface.bgcolor = AppColors.NAV_HOVER
            icon_control.color = AppColors.PRIMARY
            label_control.color = AppColors.TEXT_PRIMARY
        else:
            surface.bgcolor = None
            icon_control.color = AppColors.NAV_TEXT
            label_control.color = AppColors.NAV_TEXT
        _safe_update(surface)

    if on_click is not None:
        surface.on_hover = on_hover
        surface.mouse_cursor = ft.MouseCursor.CLICK
    return surface


def _card_title(title: str, subtitle: str) -> ft.Column:
    return ft.Column(
        spacing=2,
        controls=[
            ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
            ft.Text(subtitle, size=10, color=AppColors.TEXT_SECONDARY),
        ],
    )


class RefinedNewTestView(StableNewTestView):
    """Novo ensaio compacto em duas colunas, sem criar um segundo dono de rolagem."""

    def _compact_fields(self) -> None:
        for field in (
            self.client,
            self.process_number,
            self.product,
            self.sample_quantity,
            self.tamb,
            self.delta_t,
            self.service_temperature,
            self.ts_reference,
            self.manual_chamber_temperature,
            self.manual_chamber_humidity,
            self.manual_chamber_duration,
            self.manual_drying_temperature,
            self.manual_drying_duration,
        ):
            with suppress(Exception):
                field.height = 48
                field.dense = True
        with suppress(Exception):
            self.epl.height = 48
            self.epl.dense = True

    def _identity_compact(self) -> ft.Container:
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(1, AppColors.DIVIDER),
            border_radius=16,
            padding=16,
            content=ft.Column(
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    _card_title(
                        "Identificação",
                        "Dados essenciais do ensaio, organizados sem ocupar a tela inteira.",
                    ),
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.Container(expand=3, content=self.client),
                            ft.Container(expand=2, content=self.process_number),
                        ],
                    ),
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.Container(expand=3, content=self.product),
                            ft.Container(expand=2, content=self.sample_quantity),
                        ],
                    ),
                ],
            ),
        )

    def _thermal_compact(self) -> ft.Container:
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(1, AppColors.DIVIDER),
            border_radius=16,
            padding=16,
            content=ft.Column(
                spacing=11,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    _card_title(
                        "Configuração térmica",
                        "A regra continua calculada em tempo real; apenas o layout foi compactado.",
                    ),
                    ft.Container(
                        bgcolor=AppColors.PAGE_BACKGROUND,
                        border_radius=11,
                        border=ft.Border.all(1, AppColors.DIVIDER),
                        padding=10,
                        content=self.mode_group,
                    ),
                    self.epl,
                    self.calculated_fields,
                    self.direct_ts_fields,
                    self.manual_condition_fields,
                    self.option_panel,
                ],
            ),
        )

    def _metric(self, icon: ft.IconData, title: str, controls: list[ft.Control]) -> ft.Container:
        return ft.Container(
            expand=True,
            bgcolor=AppColors.PAGE_BACKGROUND,
            border=ft.Border.all(1, AppColors.DIVIDER),
            border_radius=14,
            padding=14,
            content=ft.Column(
                spacing=9,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Container(
                                width=34,
                                height=34,
                                border_radius=10,
                                bgcolor=AppColors.PRIMARY_LIGHT,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(icon, size=18, color=AppColors.PRIMARY),
                            ),
                            ft.Text(
                                title,
                                size=13,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                        ],
                    ),
                    *controls,
                ],
            ),
        )

    def _table17_option(self, option: str) -> ft.Container:
        status = ft.Text("Aguardando dados", size=10, color=AppColors.TEXT_SECONDARY)
        card = ft.Container(
            expand=True,
            border=ft.Border.all(1, AppColors.DIVIDER),
            border_radius=12,
            bgcolor=AppColors.SURFACE,
            padding=12,
            content=ft.Column(
                spacing=3,
                controls=[
                    ft.Text(
                        f"Alternativa {option}",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    status,
                ],
            ),
        )
        if option == "A":
            self._table17_a_status = status
            self._table17_a_card = card
        else:
            self._table17_b_status = status
            self._table17_b_card = card
        return card

    def _build_result_panel(self) -> ft.Container:
        table_a = self._table17_option("A")
        table_b = self._table17_option("B")
        self._table17_preview = ft.Container(
            border_radius=14,
            bgcolor=AppColors.INFO_LIGHT,
            border=ft.Border.all(1, AppColors.DIVIDER),
            padding=14,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Text(
                                        "Tabela 17 — alternativa aplicada",
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color=AppColors.TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        "O contorno destaca automaticamente a alternativa usada no cálculo.",
                                        size=10,
                                        color=AppColors.TEXT_SECONDARY,
                                    ),
                                ],
                            ),
                            ft.Icon(ft.Icons.TABLE_CHART_OUTLINED, color=AppColors.INFO),
                        ],
                    ),
                    ft.Row(spacing=10, controls=[table_a, table_b]),
                    self.rule_reference,
                ],
            ),
        )
        panel = ft.Container(
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(1, AppColors.DIVIDER),
            border_radius=16,
            padding=16,
            content=ft.Column(
                spacing=13,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            _card_title(
                                "Condição que será aplicada",
                                "Resumo operacional antes de salvar o cadastro.",
                            ),
                            ft.Container(
                                border_radius=12,
                                bgcolor=AppColors.PRIMARY_LIGHT,
                                border=ft.Border.all(1, AppColors.PRIMARY),
                                padding=ft.Padding.symmetric(horizontal=14, vertical=9),
                                content=ft.Row(
                                    spacing=7,
                                    controls=[
                                        ft.Text(
                                            "Ts",
                                            size=10,
                                            weight=ft.FontWeight.BOLD,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                        self.ts_value,
                                    ],
                                ),
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            self._metric(
                                ft.Icons.WATER_DROP_OUTLINED,
                                "Câmara úmida",
                                [
                                    ft.Row(
                                        wrap=True,
                                        spacing=14,
                                        controls=[
                                            self.chamber_temperature,
                                            self.chamber_humidity,
                                            self.chamber_duration,
                                        ],
                                    ),
                                    self.chamber_duration_detail,
                                ],
                            ),
                            self._metric(
                                ft.Icons.AIR,
                                "Secagem",
                                [
                                    ft.Row(
                                        wrap=True,
                                        spacing=14,
                                        controls=[
                                            self.drying_temperature,
                                            self.drying_duration,
                                        ],
                                    ),
                                    self.drying_duration_detail,
                                ],
                            ),
                        ],
                    ),
                    self._table17_preview,
                ],
            ),
        )
        self._refresh_table17_preview(update=False)
        return panel

    def _refresh_table17_preview(self, *, update: bool = True) -> None:
        selected = (self.option_group.value or "").strip().upper()
        b_disabled = bool(self.option_b.disabled)
        for option, card, status in (
            ("A", self._table17_a_card, self._table17_a_status),
            ("B", self._table17_b_card, self._table17_b_status),
        ):
            active = selected == option
            unavailable = option == "B" and b_disabled
            card.border = ft.Border.all(2 if active else 1, AppColors.PRIMARY if active else AppColors.DIVIDER)
            card.bgcolor = AppColors.PRIMARY_LIGHT if active else AppColors.SURFACE
            card.opacity = 0.55 if unavailable and not active else 1
            status.value = (
                "Aplicada ao ensaio"
                if active
                else "Indisponível para os dados informados"
                if unavailable
                else "Disponível"
                if selected
                else "Aguardando EPL e condição"
            )
            status.color = AppColors.PRIMARY if active else AppColors.TEXT_SECONDARY
            status.weight = ft.FontWeight.BOLD if active else ft.FontWeight.NORMAL
        if update:
            _safe_update(self._table17_preview)

    def _recalculate(self, event: object | None = None) -> None:
        super()._recalculate(event)
        if hasattr(self, "_table17_preview"):
            self._refresh_table17_preview()

    def _build(self) -> ft.Column:
        self._compact_fields()
        top_panels = ft.Row(
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(expand=5, content=self._identity_compact()),
                ft.Container(expand=7, content=self._thermal_compact()),
            ],
        )
        controls: list[ft.Control] = [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(
                                "Editar ensaio" if self._details else "Novo ensaio",
                                size=27,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                            ft.Text(
                                "Preencha, confira a regra aplicada e salve.",
                                size=12,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=8,
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
            ),
            _revision_banner(),
            self.error_banner,
            top_panels,
            self._notes_panel(),
        ]
        if self._details:
            controls.append(
                ft.Container(
                    bgcolor=AppColors.SURFACE,
                    border=ft.Border.all(1, AppColors.DIVIDER),
                    border_radius=16,
                    padding=16,
                    content=self.change_reason_selector.control,
                )
            )
        controls.extend([self.result_panel, ft.Container(height=10)])
        return ft.Column(
            key=f"refined-new-test-{id(self)}",
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=controls,
        )


def _severity_color(severity: str) -> str:
    if severity in {"Crítica", "Alta", "Crítico", "Alto"}:
        return AppColors.DANGER
    if severity in {"Média", "Médio"}:
        return AppColors.WARNING
    return AppColors.INFO


def _incident_log_card(incident, *, on_resolve, on_refresh) -> ft.Container:
    is_open = incident.status == "open"
    body: list[ft.Control] = [
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text(
                    f"#{incident.id} • {incident.category}",
                    size=13,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
                ft.Container(
                    border_radius=10,
                    bgcolor=AppColors.DANGER_LIGHT if is_open else AppColors.PRIMARY_LIGHT,
                    padding=ft.Padding.symmetric(horizontal=9, vertical=5),
                    content=ft.Text(
                        "Não resolvida" if is_open else "Resolvida",
                        size=9,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.DANGER if is_open else AppColors.PRIMARY,
                    ),
                ),
            ],
        ),
        ft.Text(
            f"{incident.severity} • registrada por {incident.reported_by} em "
            f"{format_datetime(incident.reported_at, assume_utc=True)}",
            size=10,
            color=_severity_color(incident.severity),
        ),
        ft.Text(incident.description, size=11, color=AppColors.TEXT_PRIMARY),
    ]
    if incident.immediate_action:
        body.append(
            ft.Text(
                f"Ação inicial: {incident.immediate_action}",
                size=10,
                color=AppColors.TEXT_SECONDARY,
            )
        )
    if incident.corrective_action:
        body.append(
            ft.Text(
                f"Fechamento: {incident.corrective_action}",
                size=10,
                color=AppColors.TEXT_SECONDARY,
            )
        )
    if not is_open and incident.resolved_by:
        resolved = (
            format_datetime(incident.resolved_at, assume_utc=True)
            if incident.resolved_at
            else "horário não informado"
        )
        body.append(
            ft.Text(
                f"Resolvida por {incident.resolved_by} em {resolved}",
                size=9,
                color=AppColors.TEXT_SECONDARY,
            )
        )

    if is_open and callable(on_resolve):
        resolve_button = ft.Button(
            content="Marcar como resolvida",
            icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
            bgcolor=AppColors.PRIMARY,
            color=AppColors.WHITE,
        )

        def confirm_resolution(_event: object | None = None) -> None:
            page = resolve_button.page
            note = ft.TextField(
                label="Observação sobre a solução (opcional)",
                hint_text="Você pode deixar em branco e apenas confirmar a resolução.",
                multiline=True,
                min_lines=2,
                max_lines=4,
                max_length=1000,
            )
            error = ft.Text("", size=10, color=AppColors.DANGER)

            def finish(_confirm_event: object | None = None) -> None:
                note_value = note.value.strip()
                action = "Falha marcada como resolvida após confirmação do administrador."
                if note_value:
                    action += f" Observação: {note_value}"
                result = on_resolve(incident.id, action)
                if result:
                    error.value = str(result)
                    _safe_update(error)
                    return
                page.pop_dialog()
                on_refresh()

            page.show_dialog(
                apply_interaction_polish(
                    styled_dialog(
                        title=f"A falha #{incident.id} já foi resolvida?",
                        subtitle="Não é obrigatório descrever todo o procedimento para alterar o status",
                        icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                        content=ft.Column(
                            width=520,
                            tight=True,
                            spacing=11,
                            controls=[
                                dialog_banner(
                                    "Se o problema ainda existir, clique em “Manter aberta”. "
                                    "Quando estiver resolvido, basta confirmar."
                                ),
                                note,
                                error,
                            ],
                        ),
                        actions=[
                            ft.TextButton(
                                content="Manter aberta",
                                on_click=lambda _close_event: page.pop_dialog(),
                            ),
                            ft.Button(
                                content="Marcar resolvida",
                                icon=ft.Icons.CHECK,
                                bgcolor=AppColors.PRIMARY,
                                color=AppColors.WHITE,
                                on_click=finish,
                            ),
                        ],
                    )
                )
            )

        resolve_button.on_click = confirm_resolution
        body.append(resolve_button)

    return ft.Container(
        bgcolor=AppColors.PAGE_BACKGROUND,
        border=ft.Border.all(1, AppColors.DIVIDER),
        border_radius=12,
        padding=13,
        content=ft.Column(spacing=7, controls=body),
    )


def _compact_incident_panel(**kwargs) -> ft.Column:
    incidents = list(kwargs["system_incidents"])
    on_report = kwargs.get("on_report_system_incident")
    on_resolve = kwargs.get("on_resolve_system_incident")
    on_refresh = kwargs["on_refresh"]
    email_settings = kwargs["email_settings"]
    open_count = sum(item.status == "open" for item in incidents)
    resolved_count = len(incidents) - open_count

    report_button = ft.Button(
        content="Registrar falha",
        icon=ft.Icons.BUG_REPORT_OUTLINED,
        bgcolor=AppColors.PRIMARY,
        color=AppColors.WHITE,
        visible=callable(on_report),
    )
    log_button = ft.Button(
        content=f"Log de falhas ({len(incidents)})",
        icon=ft.Icons.HISTORY,
    )

    def show_report(_event: object | None = None) -> None:
        page = report_button.page
        selector = ft.Dropdown(
            label="Tipo de falha",
            value="software_crash",
            options=[
                ft.DropdownOption(key=item.code, text=item.label) for item in INCIDENT_REASONS
            ],
        )
        initial = incident_reason("software_crash")
        priority = ft.Text(
            f"Prioridade automática: {initial.severity}",
            size=11,
            weight=ft.FontWeight.BOLD,
            color=_severity_color(initial.severity),
        )
        description = ft.TextField(
            label="O que aconteceu?",
            hint_text="Descreva o problema observado.",
            multiline=True,
            min_lines=3,
            max_lines=5,
            max_length=2000,
        )
        immediate = ft.TextField(
            label="Ação imediata (opcional)",
            hint_text="Pode deixar em branco se você apenas registrou a falha.",
            multiline=True,
            min_lines=2,
            max_lines=3,
            max_length=1000,
        )
        error = ft.Text("", size=10, color=AppColors.DANGER)

        def update_priority(_change_event: object | None = None) -> None:
            selected = incident_reason(selector.value or "other")
            priority.value = f"Prioridade automática: {selected.severity}"
            priority.color = _severity_color(selected.severity)
            _safe_update(priority)

        selector.on_select = update_priority

        def save(_confirm_event: object | None = None) -> None:
            description_value = description.value.strip()
            if len(description_value) < 10:
                description.error = "Descreva o problema com pelo menos 10 caracteres."
                _safe_update(description)
                return
            action_value = immediate.value.strip() or (
                "Falha registrada para avaliação; nenhuma ação imediata foi informada."
            )
            result = on_report(
                selector.value or "other",
                description_value,
                action_value,
            )
            if result:
                error.value = str(result)
                _safe_update(error)
                return
            page.pop_dialog()
            on_refresh()

        page.show_dialog(
            apply_interaction_polish(
                styled_dialog(
                    title="Registrar falha do sistema",
                    subtitle="Registro simples, com prioridade definida automaticamente",
                    icon=ft.Icons.BUG_REPORT_OUTLINED,
                    content=ft.Column(
                        width=570,
                        tight=True,
                        spacing=11,
                        controls=[
                            selector,
                            priority,
                            description,
                            immediate,
                            error,
                        ],
                    ),
                    actions=[
                        ft.TextButton(
                            content="Cancelar",
                            on_click=lambda _close_event: page.pop_dialog(),
                        ),
                        ft.Button(
                            content="Registrar",
                            icon=ft.Icons.SAVE_OUTLINED,
                            bgcolor=AppColors.PRIMARY,
                            color=AppColors.WHITE,
                            on_click=save,
                        ),
                    ],
                )
            )
        )

    def show_log(_event: object | None = None) -> None:
        page = log_button.page
        cards = [
            _incident_log_card(
                incident,
                on_resolve=on_resolve,
                on_refresh=on_refresh,
            )
            for incident in incidents
        ]
        if not cards:
            cards = [
                ft.Container(
                    padding=18,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        "Nenhuma falha foi registrada.",
                        color=AppColors.TEXT_SECONDARY,
                    ),
                )
            ]
        page.show_dialog(
            apply_interaction_polish(
                styled_dialog(
                    title="Log de falhas registradas",
                    subtitle=f"{open_count} aberta(s) • {resolved_count} resolvida(s)",
                    icon=ft.Icons.HISTORY,
                    scrollable=False,
                    content=ft.Container(
                        width=720,
                        height=500,
                        content=ft.Column(
                            scroll=ft.ScrollMode.AUTO,
                            spacing=9,
                            controls=cards,
                        ),
                    ),
                    actions=[
                        ft.Button(
                            content="Fechar",
                            on_click=lambda _close_event: page.pop_dialog(),
                        )
                    ],
                )
            )
        )

    report_button.on_click = show_report
    log_button.on_click = show_log
    email_ok = bool(email_settings.automatic_enabled)
    return ft.Column(
        spacing=12,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    _card_title(
                        "Falhas do sistema e ações corretivas",
                        "A tela mostra apenas o resumo; o histórico completo fica no log.",
                    ),
                    ft.Row(spacing=8, controls=[report_button, log_button]),
                ],
            ),
            ft.Row(
                spacing=10,
                wrap=True,
                controls=[
                    ft.Container(
                        border_radius=10,
                        bgcolor=AppColors.DANGER_LIGHT if open_count else AppColors.PRIMARY_LIGHT,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                        content=ft.Text(
                            f"{open_count} não resolvida(s)",
                            size=10,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.DANGER if open_count else AppColors.PRIMARY,
                        ),
                    ),
                    ft.Container(
                        border_radius=10,
                        bgcolor=AppColors.PAGE_BACKGROUND,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                        content=ft.Text(
                            f"{resolved_count} resolvida(s)",
                            size=10,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ),
                    ft.Container(
                        border_radius=10,
                        bgcolor=AppColors.PRIMARY_LIGHT if email_ok else AppColors.WARNING_LIGHT,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                        content=ft.Text(
                            "E-mail automático ativo" if email_ok else "E-mail automático inativo/incompleto",
                            size=10,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.PRIMARY if email_ok else AppColors.WARNING,
                        ),
                    ),
                ],
            ),
            dialog_banner(
                "Relacionado à ABNT NBR ISO/IEC 17025:2017, itens 7.10, 7.11.3 e 8.7. "
                "O registro no software não substitui o procedimento do laboratório."
            ),
        ],
    )


def _settings_builder(**kwargs) -> ft.Control:
    content = _safe_settings_builder(**kwargs)
    if isinstance(content, ft.Column):
        content.controls.insert(1, _revision_banner())
        target = next(
            (
                control
                for control in content.controls
                if isinstance(control, ft.Container)
                and any(
                    isinstance(child, ft.Text)
                    and child.value == "Falhas do sistema e ações corretivas"
                    for child in _walk(control)
                )
            ),
            None,
        )
        if isinstance(target, ft.Container):
            target.content = _compact_incident_panel(**kwargs)
    return apply_interaction_polish(content)


def _show_new_test(self) -> None:
    if not self._current_user.can_operate:
        self._show_message("Este perfil possui acesso somente para consulta.", error=True)
        return
    if self._selected_view == "new_test" and self._new_test_view is not None:
        return
    self._prepare_theme()
    view = RefinedNewTestView(
        on_cancel=self._confirm_discard_new_test,
        on_save=self._save_test,
        draft=self._new_test_draft,
    )
    view.save_button.disabled = False
    self._new_test_view = view
    self._render(view.root, selected_view="new_test")
    self._page.run_task(_force_scroll_top, view.root)


def _show_edit_test(self, test_id: int) -> None:
    if not self._current_user.can_operate:
        self._show_message("Este perfil possui acesso somente para consulta.", error=True)
        return
    self._prepare_theme()
    view = RefinedNewTestView(
        on_cancel=lambda: self.show_details(test_id),
        on_save=lambda command: self._update_test(test_id, command),
        details=self._service.get_details(test_id),
    )
    view.save_button.disabled = False
    self._render(view.root, selected_view="details")
    self._page.run_task(_force_scroll_top, view.root)


def _incident_email_sync(self) -> tuple[str, int, int]:
    """Entrega imediata com diagnóstico; a tarefa agendada continua como retentativa."""

    with legacy_app._INCIDENT_EMAIL_LOCK:
        settings = load_email_settings()
        if not settings.automatic_enabled:
            return "disabled", 0, 0
        recipients = self._auth_service.notification_admin_emails()
        if not recipients:
            return "no_admin_email", 0, 0
        delivered, failed = deliver_pending_incident_emails(
            self._repository,
            EmailNotificationProvider(settings, recipients),
        )
        return "attempted", delivered, failed


async def _deliver_incident_email_queue(self) -> None:
    try:
        status, delivered, failed = await asyncio.to_thread(_incident_email_sync, self)
    except Exception as error:
        self._show_message(
            f"Falha registrada, mas o e-mail não pôde ser enviado: {error}",
            error=True,
        )
        return
    if delivered:
        self._show_message(
            f"Falha registrada e aviso por e-mail enviado ao administrador ({delivered})."
        )
    elif failed:
        self._show_message(
            "Falha registrada, porém o SMTP recusou o e-mail. Consulte o Log de falhas e "
            "teste a configuração de e-mail.",
            error=True,
        )
    elif status == "disabled":
        self._show_message(
            "Falha registrada. O aviso interno foi criado, mas o e-mail automático está "
            "desativado ou com configuração incompleta.",
            error=True,
        )
    elif status == "no_admin_email":
        self._show_message(
            "Falha registrada. O aviso interno foi criado, mas não existe administrador ativo "
            "com e-mail cadastrado.",
            error=True,
        )


_App = production_app.ProductionClimateTestApplication


def install_round6_fixes() -> None:
    if getattr(production_app, "_round6_fixes_installed", False):
        return
    # Referências importadas por módulos antigos são substituídas explicitamente.
    interaction_module.apply_interaction_polish = apply_interaction_polish
    shell_module.apply_interaction_polish = apply_interaction_polish
    shell_module.hoverable_navigation_surface = _navigation_surface
    production_app.apply_interaction_polish = apply_interaction_polish
    production_settings_module.apply_interaction_polish = apply_interaction_polish

    _App.show_new_test = _show_new_test
    _App.show_edit_test = _show_edit_test
    _App._deliver_incident_email_queue = _deliver_incident_email_queue
    production_app.build_production_settings_view = _settings_builder
    production_settings_module.build_production_settings_view = _settings_builder
    production_app._round6_fixes_installed = True


install_round6_fixes()
main = production_app.main
