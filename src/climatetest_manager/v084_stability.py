"""Estabilização final da interface e dos fluxos críticos da versão 0.8.5.

Esta camada substitui somente pontos da R7 que reconstruíam controles já
montados. A moldura, o formulário e a Tabela 17 passam a manter uma árvore
persistente; atualizações alteram propriedades ou trocam apenas a tela central.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress
from dataclasses import replace
from decimal import Decimal

import flet as ft

from climatetest_manager import app as legacy_app
from climatetest_manager import production_app, round7_runtime
from climatetest_manager.domain.enums import ConditionInputMode
from climatetest_manager.domain.incidents import INCIDENT_REASONS, incident_reason
from climatetest_manager.round4_runtime import _force_scroll_top, _safe_settings_builder
from climatetest_manager.round6_runtime import (
    RefinedNewTestView,
    _severity_color,
    apply_interaction_polish,
)
from climatetest_manager.round7_runtime import (
    TABLE17_MODE,
    CleanNewTestView,
    _icon_heading,
    _incident_log_card_r7,
    _number,
)
from climatetest_manager.ui.components import user_avatar
from climatetest_manager.ui.components.table17_interactive import (
    InteractiveTable17,
    build_interactive_table17,
    ts_band_label,
)
from climatetest_manager.ui.responsive import (
    RESIZE_REBUILD_MIN_DELTA,
    LayoutProfile,
    viewport_width,
)
from climatetest_manager.ui.shell import build_production_shell
from climatetest_manager.ui.theme import THEME_OPTIONS, AppColors
from climatetest_manager.ui.views.final_new_test import FinalNewTestView

BUILD_REVISION = "R9-20260814"


def _safe_update(control: ft.Control | None) -> None:
    if control is None:
        return
    with suppress(RuntimeError):
        control.update()


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


def _button_label(control: ft.Control) -> str:
    if not isinstance(control, (ft.Button, ft.TextButton, ft.IconButton)):
        return ""
    content = getattr(control, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, ft.Text):
        return str(content.value or "")
    return ""


def _button_map(root: ft.Control) -> dict[str, ft.Control]:
    result: dict[str, ft.Control] = {}
    for control in _walk(root):
        label = _button_label(control)
        if label and label not in result:
            result[label] = control
    return result


def _notification_count(app: production_app.ProductionClimateTestApplication) -> int:
    try:
        return sum(
            not notification.is_read
            for notification in app._production_repository.list_user_notifications(
                user_id=app._current_user.id,
                is_admin=app._current_user.is_admin,
            )
        )
    except (OSError, RuntimeError, ValueError):
        return 0


def _compose_shell(
    app: production_app.ProductionClimateTestApplication,
    content: ft.Control,
) -> ft.Row:
    effective_layout = app._layout.with_collapsed_sidebar(app._sidebar_collapsed)
    return build_production_shell(
        content,
        selected_view=app._selected_view or "dashboard",
        on_dashboard=app.show_dashboard,
        on_tests=app.show_tests,
        on_new_test=app.show_new_test if app._current_user.can_operate else None,
        on_agenda=app.show_agenda,
        on_history=app.show_history,
        on_notifications=app.show_notifications,
        on_help=app.show_help,
        on_settings=app.show_settings,
        on_users=app.show_users if app._current_user.is_admin else None,
        on_logout=app._confirm_logout,
        on_github=app._open_github,
        on_toggle_sidebar=app._toggle_sidebar if app._layout.mode != "compact" else None,
        current_user=app._current_user,
        layout=effective_layout,
        notification_count=_notification_count(app),
    )


def _replace_shell_frame(app: production_app.ProductionClimateTestApplication) -> None:
    """Troca somente navegação e espaçamento, mantendo a tela central montada."""

    shell = getattr(app, "_v084_shell", None)
    content_host = getattr(app, "_v084_content_host", None)
    if not isinstance(shell, ft.Row) or not isinstance(content_host, ft.Container):
        return
    temporary = _compose_shell(app, ft.Container())
    sidebar = temporary.controls[0]
    temporary_host = temporary.controls[1]
    shell.controls[0] = sidebar
    if isinstance(temporary_host, ft.Container):
        content_host.padding = temporary_host.padding
        content_host.bgcolor = temporary_host.bgcolor
    _safe_update(shell)


def _stable_render(
    self: production_app.ProductionClimateTestApplication,
    content: ft.Control,
    *,
    selected_view: str,
) -> None:
    self._prepare_theme()
    apply_interaction_polish(content)
    if (
        self._selected_view == "new_test"
        and selected_view != "new_test"
        and self._new_test_view is not None
    ):
        self._new_test_draft = self._new_test_view.snapshot_draft()

    self._scroll_offset = 0.0
    self._bind_scroll_state(content)
    self._transition_index += 1
    self._current_content = content
    self._selected_view = selected_view

    shell = getattr(self, "_v084_shell", None)
    content_host = getattr(self, "_v084_content_host", None)
    if not isinstance(shell, ft.Row) or not isinstance(content_host, ft.Container):
        shell = _compose_shell(self, content)
        content_host = shell.controls[1]
        if not isinstance(content_host, ft.Container):
            raise RuntimeError("A moldura principal não possui um contêiner de conteúdo.")
        surface = ft.Container(expand=True, content=shell)
        self._v084_shell = shell
        self._v084_content_host = content_host
        self._screen_container = surface
        if not self._shell_mounted:
            self._page.clean()
            self._page.add(self._switcher)
            self._shell_mounted = True
        self._switcher.content = surface
        self._page.update()
    else:
        # Uma única atualização troca a tela e a navegação. Limpar o host e atualizá-lo
        # novamente criava uma janela intermediária vazia no WebView2.
        content_host.content = content
        _replace_shell_frame(self)

    self._page.run_task(self._save_offline_snapshot)


def _stable_toggle_sidebar(self: production_app.ProductionClimateTestApplication) -> None:
    if self._layout.mode == "compact":
        return
    self._sidebar_collapsed = not self._sidebar_collapsed
    _replace_shell_frame(self)


def _stable_handle_resize(
    self: production_app.ProductionClimateTestApplication,
    event: object | None = None,
) -> None:
    next_width = viewport_width(self._page, event)
    next_layout = LayoutProfile.stable_from_width(next_width, current_mode=self._layout.mode)
    if next_layout.mode == self._layout.mode:
        return
    if abs(next_width - self._layout_anchor_width) < RESIZE_REBUILD_MIN_DELTA:
        return
    self._layout = next_layout
    self._layout_anchor_width = next_width
    if next_layout.mode == "compact":
        self._sidebar_collapsed = False
    _replace_shell_frame(self)


def _stable_refresh_shell_frame(self: production_app.ProductionClimateTestApplication) -> None:
    _replace_shell_frame(self)


def _stable_screen_switcher() -> ft.AnimatedSwitcher:
    return ft.AnimatedSwitcher(
        content=ft.Container(expand=True),
        duration=0,
        reverse_duration=0,
        transition=ft.AnimatedSwitcherTransition.FADE,
        expand=True,
    )


def _summary_badge(label: str, value: ft.Text, icon: ft.IconData) -> ft.Container:
    return ft.Container(
        expand=True,
        border_radius=11,
        bgcolor=AppColors.PAGE_BACKGROUND,
        border=ft.Border.all(1, AppColors.DIVIDER),
        padding=11,
        content=ft.Row(
            spacing=8,
            controls=[
                ft.Icon(icon, size=17, color=AppColors.PRIMARY),
                ft.Column(
                    spacing=1,
                    controls=[
                        ft.Text(label, size=9, color=AppColors.TEXT_SECONDARY),
                        value,
                    ],
                ),
            ],
        ),
    )


class StableNewTestView(CleanNewTestView):
    """Novo ensaio sem controles duplicados nem substituição durante a rolagem."""

    _interactive_table: InteractiveTable17

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._table17_guide.content = ft.Container(
            border_radius=12,
            bgcolor=AppColors.INFO_LIGHT,
            border=ft.Border.all(1, AppColors.DIVIDER),
            padding=11,
            content=ft.Row(
                spacing=9,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Icon(ft.Icons.TOUCH_APP_OUTLINED, size=18, color=AppColors.PRIMARY),
                    ft.Text(
                        "Depois de informar o Ts, escolha um EPL e uma condição na tabela. "
                        "Células acinzentadas explicam por que não são aplicáveis.",
                        expand=True,
                        size=10,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                ],
            ),
        )
        if self._table17_guide not in self._refresh_targets:
            self._refresh_targets = (*self._refresh_targets, self._table17_guide)
        self._on_mode_change()

    def _simple_summary(self) -> ft.Control:
        self._simple_epl = ft.Text(
            "—", size=11, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY
        )
        self._simple_band = ft.Text(
            "Aguardando seleção",
            size=11,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
        )
        self._simple_option = ft.Text(
            "—", size=11, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY
        )
        return ft.Column(
            spacing=11,
            controls=[
                ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        self._metric(
                            ft.Icons.WATER_DROP_OUTLINED,
                            "Câmara úmida",
                            [
                                ft.Row(
                                    wrap=True,
                                    spacing=12,
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
                                    spacing=12,
                                    controls=[self.drying_temperature, self.drying_duration],
                                ),
                                self.drying_duration_detail,
                            ],
                        ),
                    ],
                ),
                ft.Row(
                    spacing=9,
                    controls=[
                        _summary_badge("EPL", self._simple_epl, ft.Icons.SHIELD_OUTLINED),
                        _summary_badge("Faixa de Ts", self._simple_band, ft.Icons.THERMOSTAT),
                        _summary_badge(
                            "Configuração",
                            self._simple_option,
                            ft.Icons.CHECK_CIRCLE_OUTLINE,
                        ),
                    ],
                ),
            ],
        )

    def _advanced_table(self) -> InteractiveTable17:
        ts = self._current_ts()
        return build_interactive_table17(
            ts=ts,
            selected_epl=self.epl.value,
            selected_option=self.option_group.value,
            on_select_epl=self._select_table_epl,
            on_select_option=self._select_table_option,
            on_invalid=self._show_table_error,
        )

    def _build_result_panel(self) -> ft.Container:
        self._simple_button = ft.Button(
            content="Visualização simples",
            icon=ft.Icons.DASHBOARD_OUTLINED,
            bgcolor=AppColors.PRIMARY,
            color=AppColors.WHITE,
            on_click=lambda _event: self._set_table_view("simple"),
        )
        self._advanced_button = ft.Button(
            content="Visualização avançada",
            icon=ft.Icons.TABLE_CHART_OUTLINED,
            color=AppColors.PRIMARY,
            on_click=lambda _event: self._set_table_view("advanced"),
        )
        self._simple_holder = ft.Container(content=self._simple_summary())
        self._interactive_table = self._advanced_table()
        self._advanced_holder = ft.Container(visible=False, content=self._interactive_table)
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(1, AppColors.DIVIDER),
            border_radius=16,
            padding=16,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Row(
                        wrap=True,
                        run_spacing=8,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            _icon_heading(
                                ft.Icons.TUNE,
                                "Condição que será aplicada",
                                "Resumo simples ou conferência direta na Tabela 17.",
                            ),
                            ft.Row(
                                spacing=7,
                                controls=[self._simple_button, self._advanced_button],
                            ),
                        ],
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.Container(
                                border_radius=11,
                                bgcolor=AppColors.PRIMARY_LIGHT,
                                border=ft.Border.all(1, AppColors.PRIMARY),
                                padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                                content=self.ts_value,
                            )
                        ],
                    ),
                    self._simple_holder,
                    self._advanced_holder,
                ],
            ),
        )

    def _current_ts(self) -> Decimal | None:
        if self.mode_group.value in {ConditionInputMode.DIRECT_TS.value, TABLE17_MODE}:
            return _number(self.service_temperature.value)
        if self._condition is not None:
            return self._condition.service_temperature_c
        return None

    def _show_table_error(self, message: str) -> None:
        self._show_error(message)
        self._refresh()

    def _set_table_view(self, mode: str) -> None:
        self._table_view = mode
        self._simple_holder.visible = mode == "simple"
        self._advanced_holder.visible = mode == "advanced"
        if self._simple_button is not None:
            self._simple_button.bgcolor = AppColors.PRIMARY if mode == "simple" else None
            self._simple_button.color = AppColors.WHITE if mode == "simple" else AppColors.PRIMARY
        if self._advanced_button is not None:
            self._advanced_button.bgcolor = AppColors.PRIMARY if mode == "advanced" else None
            self._advanced_button.color = (
                AppColors.WHITE if mode == "advanced" else AppColors.PRIMARY
            )
        _safe_update(getattr(self, "result_panel", None))

    def _refresh_result_views(self) -> None:
        if not hasattr(self, "_interactive_table"):
            return
        ts = self._current_ts()
        epl = self.epl.value or "—"
        option = self.option_group.value or "—"
        self._simple_epl.value = epl
        self._simple_band.value = ts_band_label(self.epl.value, ts)
        self._simple_option.value = f"Opção {option}" if option != "—" else "—"
        self._interactive_table.set_state(
            ts=ts,
            selected_epl=self.epl.value,
            selected_option=self.option_group.value,
        )
        _safe_update(getattr(self, "result_panel", None))

    def _on_mode_change(self, event: object | None = None) -> None:
        mode = self.mode_group.value or ConditionInputMode.CALCULATED.value
        if mode != TABLE17_MODE:
            self._table17_guide.visible = False
            self.epl.visible = True
            RefinedNewTestView._on_mode_change(self, event)
            if hasattr(self, "save_button"):
                self.save_button.disabled = False
            return
        self.calculated_fields.visible = False
        self.direct_ts_fields.visible = True
        self.manual_condition_fields.visible = False
        self.option_panel.visible = False
        self.epl.visible = False
        self._table17_guide.visible = True
        self.manual_drying_fields.visible = False
        self._set_table_view("advanced")
        self._recalculate()

    def _recalculate(self, event: object | None = None) -> None:
        if self.mode_group.value == TABLE17_MODE:
            CleanNewTestView._recalculate(self, event)
        else:
            RefinedNewTestView._recalculate(self, event)
            self._refresh_result_views()
        if hasattr(self, "save_button"):
            self.save_button.disabled = False
            _safe_update(self.save_button)

    def _submit(self, event: object | None = None) -> None:
        if self.mode_group.value != TABLE17_MODE:
            RefinedNewTestView._submit(self, event)
            return
        original = self.mode_group.value
        self.mode_group.value = ConditionInputMode.DIRECT_TS.value
        try:
            RefinedNewTestView._submit(self, event)
        finally:
            self.mode_group.value = original


def _hold_button(
    page: ft.Page,
    *,
    label: str,
    on_confirm: Callable[[], None],
    enabled: Callable[[], bool] | None = None,
) -> ft.Control:
    """Confirmação por pressão com progresso integrado no próprio botão."""

    progress = ft.ProgressBar(
        value=0,
        height=56,
        color=AppColors.DANGER,
        bgcolor=AppColors.DANGER_LIGHT,
    )
    icon = ft.Icon(ft.Icons.TOUCH_APP_OUTLINED, size=19, color=AppColors.DANGER)
    caption = ft.Text(
        label,
        size=11,
        weight=ft.FontWeight.BOLD,
        color=AppColors.DANGER,
        no_wrap=True,
    )
    hint = ft.Text(
        "Segure por 1,6 s • solte para abortar",
        size=8,
        color=AppColors.TEXT_SECONDARY,
        no_wrap=True,
    )
    percent = ft.Text("0%", size=10, weight=ft.FontWeight.BOLD, color=AppColors.DANGER)
    state = {"holding": False, "generation": 0, "confirmed": False}

    async def advance(generation: int) -> None:
        for step in range(1, 25):
            await asyncio.sleep(0.065)
            if not state["holding"] or state["generation"] != generation:
                return
            value = step / 24
            progress.value = value
            percent.value = f"{round(value * 100)}%"
            if value >= 0.16:
                icon.color = AppColors.WHITE
            if value >= 0.44:
                caption.color = AppColors.WHITE
            if value >= 0.52:
                hint.color = AppColors.WHITE
            if value >= 0.88:
                percent.color = AppColors.WHITE
            _safe_update(surface)
        state["holding"] = False
        state["confirmed"] = True
        if enabled is not None and not enabled():
            reset()
            return
        caption.value = "Confirmando ação..."
        hint.value = "Aguarde um instante"
        _safe_update(surface)
        on_confirm()

    def reset() -> None:
        progress.value = 0
        percent.value = "0%"
        icon.color = AppColors.DANGER
        caption.color = AppColors.DANGER
        caption.value = label
        hint.color = AppColors.TEXT_SECONDARY
        hint.value = "Segure por 1,6 s • solte para abortar"
        percent.color = AppColors.DANGER
        _safe_update(surface)

    def down(_event: object | None = None) -> None:
        state["generation"] += 1
        state["holding"] = True
        state["confirmed"] = False
        reset()
        page.run_task(advance, state["generation"])

    def release(_event: object | None = None) -> None:
        state["holding"] = False
        state["generation"] += 1
        if not state["confirmed"]:
            reset()

    surface = ft.Container(
        height=56,
        border=ft.Border.all(1, AppColors.DANGER),
        border_radius=12,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        animate=ft.Animation(120, ft.AnimationCurve.EASE_OUT_CUBIC),
        content=ft.Stack(
            controls=[
                progress,
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=12, vertical=0),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=34,
                                height=34,
                                border_radius=17,
                                border=ft.Border.all(1, AppColors.DANGER),
                                alignment=ft.Alignment.CENTER,
                                content=icon,
                            ),
                            ft.Container(
                                expand=True,
                                padding=ft.Padding.symmetric(horizontal=8),
                                alignment=ft.Alignment.CENTER,
                                content=ft.Column(
                                    tight=True,
                                    spacing=0,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[caption, hint],
                                ),
                            ),
                            ft.Container(
                                width=38,
                                alignment=ft.Alignment.CENTER_RIGHT,
                                content=percent,
                            ),
                        ],
                    ),
                ),
            ]
        ),
    )
    return ft.GestureDetector(
        on_tap_down=down,
        on_tap_up=release,
        on_tap_cancel=release,
        mouse_cursor=ft.MouseCursor.CLICK,
        content=surface,
    )


def _status_pill(text: str, *, active: bool, warning: bool = False) -> ft.Container:
    color = AppColors.WARNING if warning else AppColors.PRIMARY if active else AppColors.DANGER
    background = (
        AppColors.WARNING_LIGHT
        if warning
        else AppColors.PRIMARY_LIGHT
        if active
        else AppColors.DANGER_LIGHT
    )
    return ft.Container(
        border_radius=16,
        bgcolor=background,
        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
        content=ft.Text(text, size=9, weight=ft.FontWeight.BOLD, color=color),
    )


def _settings_card(
    *,
    icon: ft.IconData,
    title: str,
    subtitle: str,
    status: ft.Control | None,
    body: list[ft.Control],
    height: int = 226,
) -> ft.Container:
    heading = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[
            _icon_heading(icon, title, subtitle),
            *([status] if status is not None else []),
        ],
    )
    return ft.Container(
        height=height,
        bgcolor=AppColors.SURFACE,
        border=ft.Border.all(1, AppColors.DIVIDER),
        border_radius=16,
        padding=16,
        content=ft.Column(
            spacing=11,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[heading, *body],
        ),
    )


def _compact_incident_panel(**kwargs) -> ft.Control:
    """Resumo limpo com classificação controlada e log separado."""

    incidents = list(kwargs.get("system_incidents") or [])
    on_report = kwargs.get("on_report_system_incident")
    on_resolve = kwargs.get("on_resolve_system_incident")
    on_refresh = kwargs["on_refresh"]
    open_count = sum(item.status == "open" for item in incidents)
    resolved_count = len(incidents) - open_count
    report_button = ft.Button(
        content="Registrar falha",
        icon=ft.Icons.ADD_CIRCLE_OUTLINE,
        disabled=not callable(on_report),
    )
    log_button = ft.Button(
        content="Abrir log de falhas",
        icon=ft.Icons.RECEIPT_LONG_OUTLINED,
    )

    def report(_event: object | None = None) -> None:
        if not callable(on_report):
            return
        page = report_button.page
        selector = ft.Dropdown(
            label="Tipo de falha",
            value="software_crash",
            options=[
                ft.DropdownOption(key=item.code, text=item.label) for item in INCIDENT_REASONS
            ],
        )
        initial = incident_reason(selector.value)
        priority = ft.Text(
            f"Prioridade automática: {initial.severity}",
            size=10,
            weight=ft.FontWeight.BOLD,
            color=_severity_color(initial.severity),
        )
        description = ft.TextField(
            label="O que aconteceu?",
            hint_text="Descreva o problema observado e quando ele ocorreu.",
            multiline=True,
            min_lines=3,
            max_lines=5,
            max_length=2000,
        )
        immediate = ft.TextField(
            label="Ação imediata (opcional)",
            hint_text="Ex.: operação interrompida e registros conferidos.",
            multiline=True,
            min_lines=2,
            max_lines=3,
            max_length=1000,
        )
        error = ft.Text("", size=10, color=AppColors.DANGER)

        def update_priority(_change: object | None = None) -> None:
            selected = incident_reason(selector.value or "other")
            priority.value = f"Prioridade automática: {selected.severity}"
            priority.color = _severity_color(selected.severity)
            _safe_update(priority)

        def save(_confirm: object | None = None) -> None:
            description_value = description.value.strip()
            if len(description_value) < 10:
                description.error = "Descreva a falha com pelo menos 10 caracteres."
                _safe_update(description)
                return
            action = immediate.value.strip() or (
                "Falha registrada para avaliação; nenhuma ação imediata foi informada."
            )
            result = on_report(selector.value or "other", description_value, action)
            if result:
                error.value = str(result)
                _safe_update(error)
                return
            page.pop_dialog()
            on_refresh()

        selector.on_select = update_priority
        page.show_dialog(
            apply_interaction_polish(
                round7_runtime.styled_dialog(
                    title="Registrar falha",
                    subtitle="O aviso interno é criado e o e-mail é tentado imediatamente",
                    icon=ft.Icons.BUG_REPORT_OUTLINED,
                    content=ft.Column(
                        width=560,
                        tight=True,
                        spacing=10,
                        controls=[selector, priority, description, immediate, error],
                    ),
                    actions=[
                        ft.TextButton(
                            content="Cancelar",
                            on_click=lambda _close: page.pop_dialog(),
                        ),
                        ft.Button(
                            content="Registrar",
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
        log_open = {"value": True}

        def close_log() -> None:
            if not log_open["value"]:
                return
            log_open["value"] = False
            with suppress(Exception):
                page.pop_dialog()

        cards = [
            _incident_log_card_r7(
                incident,
                on_resolve=on_resolve,
                close_log=close_log,
                on_refresh=on_refresh,
            )
            for incident in incidents
        ] or [ft.Text("Nenhuma falha registrada.", color=AppColors.TEXT_SECONDARY)]
        page.show_dialog(
            apply_interaction_polish(
                round7_runtime.styled_dialog(
                    title="Log de falhas",
                    subtitle=f"{open_count} não resolvida(s) • {resolved_count} resolvida(s)",
                    icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                    content=ft.Container(
                        width=700,
                        height=480,
                        content=ft.Column(
                            scroll=ft.ScrollMode.AUTO,
                            spacing=8,
                            controls=cards,
                        ),
                    ),
                    actions=[ft.Button(content="Fechar", on_click=lambda _close: close_log())],
                )
            )
        )

    report_button.on_click = report
    log_button.on_click = show_log
    return ft.Column(
        spacing=11,
        controls=[
            _icon_heading(
                ft.Icons.GPP_MAYBE_OUTLINED,
                "Falhas do sistema e ações corretivas",
                "Resumo das ocorrências registradas.",
            ),
            ft.Row(
                spacing=8,
                wrap=True,
                controls=[
                    ft.Container(
                        border_radius=10,
                        bgcolor=(AppColors.DANGER_LIGHT if open_count else AppColors.PRIMARY_LIGHT),
                        padding=ft.Padding.symmetric(horizontal=12, vertical=7),
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
                        padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                        content=ft.Text(f"{resolved_count} resolvida(s)", size=10),
                    ),
                ],
            ),
            ft.Row(spacing=8, wrap=True, controls=[report_button, log_button]),
        ],
    )


def _activate_automatic_email(kwargs: dict, button: ft.Button) -> None:
    settings = kwargs["email_settings"]
    result = kwargs["on_save_email_settings"](replace(settings, enabled=True), "")
    if not result:
        return
    page = button.page
    page.show_dialog(
        ft.SnackBar(
            content=str(result),
            bgcolor=AppColors.DANGER,
            show_close_icon=True,
        )
    )


def _compact_settings_builder(**kwargs) -> ft.Control:
    """Configurações em grade 2x2, mantendo todos os diálogos validados."""

    base = _safe_settings_builder(**kwargs)
    buttons = _button_map(base)
    current_user = kwargs["current_user"]
    email_settings = kwargs["email_settings"]
    backup_directory = kwargs["backup_directory"]
    notifications_enabled = bool(kwargs["notifications_enabled"])
    identity = kwargs["identity"]

    email_actions: list[ft.Control] = []
    configured_button = buttons.get("Configurar e-mail")
    if configured_button is not None:
        email_actions.append(configured_button)
    email_actions.append(
        ft.Button(
            content="Testar e-mail",
            icon=ft.Icons.SEND_OUTLINED,
            disabled=not email_settings.has_credentials,
            on_click=lambda _event: kwargs["on_test_email"](),
        )
    )
    if email_settings.has_credentials and not email_settings.enabled:
        activate_email = ft.Button(
            content="Ativar automação",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=AppColors.PRIMARY,
            color=AppColors.WHITE,
        )
        activate_email.on_click = lambda _event: _activate_automatic_email(kwargs, activate_email)
        email_actions.append(activate_email)

    if email_settings.automatic_enabled:
        email_status = _status_pill("Automático ativo", active=True)
        email_note = "Alertas e prazos são enviados automaticamente aos usuários ativos."
    elif email_settings.has_credentials:
        email_status = _status_pill("Automação desativada", active=False, warning=True)
        email_note = (
            "O teste SMTP funciona, mas os alertas automáticos ainda precisam ser ativados."
        )
    else:
        email_status = _status_pill("Não configurado", active=False)
        email_note = "Configure uma conta SMTP para enviar alertas e prazos por e-mail."

    email_card = _settings_card(
        icon=ft.Icons.MAIL_OUTLINE,
        title="Avisos por e-mail",
        subtitle="Alertas operacionais e falhas do sistema.",
        status=email_status,
        body=[
            ft.Text(email_note, size=10, color=AppColors.TEXT_SECONDARY),
            ft.Row(wrap=True, run_spacing=7, spacing=7, controls=email_actions),
        ],
    )

    notification_card = _settings_card(
        icon=ft.Icons.NOTIFICATIONS_NONE,
        title="Avisos em segundo plano",
        subtitle="Notificações mesmo com a janela minimizada.",
        status=_status_pill(
            "Ativo" if notifications_enabled else "Inativo",
            active=notifications_enabled,
        ),
        body=[
            ft.Text(
                "O servidor verifica prazos; cada estação recebe o aviso no próprio Windows.",
                size=10,
                color=AppColors.TEXT_SECONDARY,
            ),
            ft.Row(
                wrap=True,
                run_spacing=7,
                spacing=7,
                controls=[
                    ft.Button(
                        content="Testar notificação",
                        icon=ft.Icons.NOTIFICATIONS,
                        on_click=lambda _event: kwargs["on_test_notification"](),
                    ),
                    ft.Button(
                        content="Ativar avisos",
                        icon=ft.Icons.PLAY_ARROW,
                        disabled=notifications_enabled,
                        on_click=lambda _event: kwargs["on_enable_notifications"](),
                    ),
                    ft.Button(
                        content="Desativar avisos",
                        icon=ft.Icons.PAUSE_CIRCLE_OUTLINE,
                        disabled=not notifications_enabled,
                        color=AppColors.DANGER,
                        on_click=lambda _event: kwargs["on_disable_notifications"](),
                    ),
                ],
            ),
        ],
    )

    backup_card = _settings_card(
        icon=ft.Icons.CLOUD_UPLOAD_OUTLINED,
        title="Backup automático",
        subtitle="Cópias verificadas sem tocar no banco ativo.",
        status=_status_pill(
            "Configurado" if backup_directory is not None else "Pasta pendente",
            active=backup_directory is not None,
            warning=backup_directory is None,
        ),
        body=[
            ft.Text(
                str(backup_directory)
                if backup_directory is not None
                else "Selecione uma pasta externa.",
                size=10,
                color=AppColors.TEXT_SECONDARY,
                no_wrap=True,
                tooltip=str(backup_directory) if backup_directory is not None else None,
            ),
            ft.Row(
                wrap=True,
                run_spacing=7,
                spacing=7,
                controls=[
                    ft.Button(
                        content="Selecionar pasta",
                        icon=ft.Icons.FOLDER_OPEN,
                        disabled=kwargs["on_configure_backup"] is None,
                        on_click=kwargs["on_configure_backup"],
                    ),
                    ft.Button(
                        content="Criar cópia agora",
                        icon=ft.Icons.BACKUP,
                        on_click=kwargs["on_backup"],
                    ),
                ],
            ),
        ],
    )

    incident_panel = _compact_incident_panel(**kwargs)
    incident_card = ft.Container(
        height=226,
        bgcolor=AppColors.SURFACE,
        border=ft.Border.all(1, AppColors.DIVIDER),
        border_radius=16,
        padding=16,
        content=incident_panel,
    )

    grid_controls: list[ft.Control] = []
    if current_user.is_admin:
        grid_controls.append(ft.Container(col={"xs": 12, "md": 6}, content=email_card))
    grid_controls.extend(
        [
            ft.Container(col={"xs": 12, "md": 6}, content=notification_card),
            ft.Container(col={"xs": 12, "md": 6}, content=backup_card),
            ft.Container(col={"xs": 12, "md": 6}, content=incident_card),
        ]
    )

    theme = ft.Dropdown(
        label="Tema deste computador",
        value=(
            kwargs["theme_mode"]
            if kwargs["theme_mode"] in {item[0] for item in THEME_OPTIONS}
            else "light"
        ),
        options=[
            ft.DropdownOption(key=key, text=f"{label} — {description}")
            for key, label, description in THEME_OPTIONS
        ],
        expand=True,
    )
    theme.on_select = lambda _event: kwargs["on_theme_change"](theme.value or "light")

    account_actions = [
        buttons[label]
        for label in (
            "Escolher foto",
            "Remover foto",
            "Alterar minha senha",
            "Gerenciar usuários",
            "Renovar código de recuperação",
            "Guia de uso",
        )
        if label in buttons
    ]
    account_card = ft.Container(
        col={"xs": 12, "md": 6},
        content=_settings_card(
            icon=ft.Icons.PERSON_OUTLINE,
            title="Conta e acesso",
            subtitle=f"@{current_user.username} • {current_user.role_label}",
            status=None,
            height=208,
            body=[
                ft.Row(
                    spacing=10,
                    controls=[
                        user_avatar(current_user, size=42),
                        ft.Text(
                            f"{current_user.full_name}\n{current_user.email}",
                            size=10,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
                ft.Row(wrap=True, run_spacing=7, spacing=7, controls=account_actions),
            ],
        ),
    )
    appearance_card = ft.Container(
        col={"xs": 12, "md": 6},
        content=_settings_card(
            icon=ft.Icons.PALETTE_OUTLINED,
            title="Aparência",
            subtitle="Preferência salva somente nesta estação.",
            status=None,
            height=208,
            body=[theme],
        ),
    )

    address_text = ", ".join(identity.addresses) or "Aguardando endereço de rede"
    server_card = ft.Container(
        bgcolor=AppColors.SURFACE,
        border=ft.Border.all(1, AppColors.DIVIDER),
        border_radius=16,
        padding=16,
        content=ft.Row(
            wrap=True,
            run_spacing=8,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                _icon_heading(
                    ft.Icons.DNS_OUTLINED,
                    "Servidor central",
                    "Uma única fonte de dados para todas as estações da rede.",
                ),
                ft.Text(
                    f"{identity.hostname}:{identity.port} • {address_text}",
                    size=10,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.PRIMARY,
                    selectable=True,
                ),
                _status_pill("Ativo na rede", active=True),
            ],
        ),
    )

    root = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=14,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            ft.Column(
                spacing=2,
                controls=[
                    ft.Text(
                        "Configurações",
                        size=27,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        "Preferências, avisos, cópias e integridade do sistema.",
                        size=12,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                ],
            ),
            ft.ResponsiveRow(spacing=14, run_spacing=14, controls=grid_controls),
            ft.ResponsiveRow(
                spacing=14,
                run_spacing=14,
                controls=[appearance_card, account_card],
            ),
            server_card,
            ft.Container(height=8),
        ],
    )
    return apply_interaction_polish(root)


def _show_new_test(self: production_app.ProductionClimateTestApplication) -> None:
    if not self._current_user.can_operate:
        self._show_message("Este perfil possui acesso somente para consulta.", error=True)
        return
    if self._selected_view == "new_test" and self._new_test_view is not None:
        return
    self._prepare_theme()
    view = FinalNewTestView(
        on_cancel=self._confirm_discard_new_test,
        on_save=self._save_test,
        draft=self._new_test_draft,
    )
    view.save_button.disabled = False
    self._new_test_view = view
    self._render(view.root, selected_view="new_test")
    self._page.run_task(_force_scroll_top, view.root)


def _show_edit_test(
    self: production_app.ProductionClimateTestApplication,
    test_id: int,
) -> None:
    if not self._current_user.can_operate:
        self._show_message("Este perfil possui acesso somente para consulta.", error=True)
        return
    self._prepare_theme()
    view = FinalNewTestView(
        on_cancel=lambda: self.show_details(test_id),
        on_save=lambda command: self._update_test(test_id, command),
        details=self._service.get_details(test_id),
    )
    view.save_button.disabled = False
    self._render(view.root, selected_view="details")
    self._page.run_task(_force_scroll_top, view.root)


def install() -> None:
    if getattr(production_app, "_v084_stability_installed", False):
        return
    application = production_app.ProductionClimateTestApplication
    legacy_app._screen_switcher = _stable_screen_switcher
    application._render = _stable_render
    application._toggle_sidebar = _stable_toggle_sidebar
    application._handle_resize = _stable_handle_resize
    application._refresh_shell_frame = _stable_refresh_shell_frame
    application.show_new_test = _show_new_test
    application.show_edit_test = _show_edit_test
    round7_runtime._hold_control = _hold_button
    production_app.build_production_settings_view = _compact_settings_builder
    production_app._v084_stability_installed = True
