"""Rodada 4: estabiliza as telas críticas sem reparentar controles Flet.

A rodada anterior corrigiu regras e integrações, porém ainda reconstruía partes da
árvore visual em tempo de execução. Em Flet isso pode deixar controles com dois
pais lógicos ou preservar offsets de rolagem indevidos. Este módulo mantém todas
as correções anteriores e substitui somente as composições que apresentaram falha
visual no Windows real.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime

import flet as ft

from climatetest_manager import production_app
from climatetest_manager.domain.enums import ConditionInputMode
from climatetest_manager.domain.incidents import INCIDENT_REASONS, incident_reason
from climatetest_manager.round3_runtime import install_round3_fixes
from climatetest_manager.round3_runtime import _polished_clear_condition
from climatetest_manager.round3_runtime import _polished_recalculate
from climatetest_manager.round3_runtime import _polished_submit
from climatetest_manager.ui.components import dialog_actions, dialog_banner, styled_dialog
from climatetest_manager.ui.formatters import format_datetime
from climatetest_manager.ui.interaction import apply_interaction_polish
from climatetest_manager.ui.theme import AppColors
from climatetest_manager.ui.views import production_settings as production_settings_module
from climatetest_manager.ui.views.new_test import NewTestDraft, NewTestView
from climatetest_manager.ui.views.server_status import build_server_status_card
from climatetest_manager.ui.views.test_details import TestDetailsView

install_round3_fixes()


def _safe_update(control: ft.Control) -> None:
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
        return content.value or ""
    return ""


def _panel(title: str, body: list[ft.Control], *, help_text: str = "") -> ft.Container:
    title_controls: list[ft.Control] = [
        ft.Text(
            title,
            size=16,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
        )
    ]
    if help_text:
        title_controls.append(
            ft.Text(help_text, size=11, color=AppColors.TEXT_SECONDARY)
        )
    return ft.Container(
        bgcolor=AppColors.SURFACE,
        border=ft.Border.all(1, AppColors.DIVIDER),
        border_radius=16,
        padding=18,
        content=ft.Column(
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[ft.Column(spacing=3, controls=title_controls), *body],
        ),
    )


class SafeNewTestView(NewTestView):
    """Formulário vertical: uma única rolagem e nenhum controle é reparentado."""

    def _build_result_panel(self) -> ft.Container:
        return _panel(
            "Prévia da condição",
            [
                ft.Container(
                    border_radius=12,
                    bgcolor=AppColors.PRIMARY_LIGHT,
                    border=ft.Border.all(1, AppColors.DIVIDER),
                    padding=14,
                    content=ft.Column(
                        spacing=6,
                        controls=[
                            ft.Text(
                                "Temperatura de serviço / referência",
                                size=10,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                            self.ts_value,
                        ],
                    ),
                ),
                ft.Row(
                    wrap=True,
                    run_spacing=8,
                    spacing=18,
                    controls=[
                        ft.Text("Câmara:", weight=ft.FontWeight.BOLD),
                        self.chamber_temperature,
                        self.chamber_humidity,
                        self.chamber_duration,
                    ],
                ),
                self.chamber_duration_detail,
                ft.Row(
                    wrap=True,
                    run_spacing=8,
                    spacing=18,
                    controls=[
                        ft.Text("Secagem:", weight=ft.FontWeight.BOLD),
                        self.drying_temperature,
                        self.drying_duration,
                    ],
                ),
                self.drying_duration_detail,
                self.rule_reference,
            ],
            help_text="Confira o resultado antes de salvar o cadastro.",
        )

    def _build(self) -> ft.ListView:
        title = "Editar ensaio" if self._details else "Novo ensaio"
        subtitle = (
            "Corrija os dados e informe o motivo da alteração."
            if self._details
            else "Preencha os campos; a condição é calculada em tempo real."
        )
        controls: list[ft.Control] = [
            ft.Column(
                spacing=4,
                controls=[
                    ft.Text(
                        title,
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    ft.Text(subtitle, size=13, color=AppColors.TEXT_SECONDARY),
                ],
            ),
            ft.Row(
                wrap=True,
                spacing=8,
                run_spacing=8,
                controls=[
                    ft.Button(
                        content="Cancelar",
                        icon=ft.Icons.CLOSE,
                        on_click=lambda _event: self._on_cancel(),
                    ),
                    self.save_button,
                ],
            ),
            self.error_banner,
            _panel(
                "Identificação do ensaio",
                [
                    self.client,
                    self.process_number,
                    self.sample_quantity,
                    self.product,
                ],
                help_text="Cliente, processo, produto e quantidade de amostras.",
            ),
            _panel(
                "Condição térmica",
                [
                    ft.Container(
                        bgcolor=AppColors.PAGE_BACKGROUND,
                        border=ft.Border.all(1, AppColors.DIVIDER),
                        border_radius=12,
                        padding=12,
                        content=ft.Column(
                            spacing=6,
                            controls=[
                                ft.Text(
                                    "Origem da condição",
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                                self.mode_group,
                            ],
                        ),
                    ),
                    self.epl,
                    self.calculated_fields,
                    self.direct_ts_fields,
                    self.manual_condition_fields,
                    self.option_panel,
                ],
                help_text="Apenas os campos aplicáveis ao modo escolhido ficam visíveis.",
            ),
            _panel("Observações", [self.notes]),
        ]
        if self._details:
            controls.append(
                _panel(
                    "Motivo da alteração",
                    [self.change_reason_selector.control],
                    help_text="Obrigatório para manter a rastreabilidade.",
                )
            )
        controls.extend([self.result_panel, ft.Container(height=10)])
        return ft.ListView(
            key=f"safe-new-test-{id(self)}",
            expand=True,
            spacing=16,
            controls=controls,
        )

    def _clear_condition(self, help_text: str) -> None:
        _polished_clear_condition(self, help_text)

    def _recalculate(self, event: object | None = None) -> None:
        _polished_recalculate(self, event)

    def _submit(self, event: object | None = None) -> None:
        _polished_submit(self, event)


async def _force_scroll_top(control: ft.Control) -> None:
    await asyncio.sleep(0.05)
    if not isinstance(control, ft.ScrollableControl):
        return
    with suppress(RuntimeError):
        await control.scroll_to(offset=0, duration=0)


def _disable_viewer_actions(root: ft.Control) -> None:
    for control in _walk(root):
        if isinstance(control, ft.Button):
            control.visible = False


def _show_admin_delete_dialog(app, test_id: int) -> None:
    page = app._page
    reason = ft.TextField(
        label="Motivo da exclusão *",
        hint_text="Ex.: cadastro fictício criado somente para validação.",
        multiline=True,
        min_lines=2,
        max_lines=4,
        max_length=500,
        bgcolor=AppColors.SURFACE,
        border_color=AppColors.DIVIDER,
        focused_border_color=AppColors.PRIMARY,
    )
    error = ft.Text("", size=11, color=AppColors.DANGER)

    def confirm(_event: object | None = None) -> None:
        value = reason.value.strip()
        if len(value) < 10:
            reason.error = "Informe um motivo com pelo menos 10 caracteres."
            error.value = "A justificativa é obrigatória para preservar a auditoria."
            _safe_update(reason)
            _safe_update(error)
            return
        page.pop_dialog()
        app._delete_test_as_admin(test_id, value)

    page.show_dialog(
        styled_dialog(
            title=f"Excluir ensaio #{test_id} do histórico?",
            subtitle="Operação restrita ao administrador",
            icon=ft.Icons.DELETE_FOREVER_OUTLINED,
            danger=True,
            content=ft.Column(
                width=540,
                tight=True,
                spacing=12,
                controls=[
                    dialog_banner(
                        "O ensaio será removido das telas operacionais. A exclusão continuará "
                        "registrada no Registro de atividades.",
                        icon=ft.Icons.WARNING_AMBER,
                        danger=True,
                    ),
                    reason,
                    error,
                ],
            ),
            actions=dialog_actions(
                page=page,
                primary_label="Excluir do histórico",
                primary_icon=ft.Icons.DELETE_FOREVER,
                on_confirm=confirm,
                danger=True,
                cancel_label="Cancelar",
            ),
        )
    )


def _incident_card(incident, *, on_resolve, on_refresh) -> ft.Container:
    is_open = incident.status == "open"
    severity_color = (
        AppColors.DANGER
        if incident.severity in {"Crítica", "Alta", "Crítico", "Alto"}
        else AppColors.WARNING
        if incident.severity in {"Média", "Médio"}
        else AppColors.INFO
    )
    body: list[ft.Control] = [
        ft.Text(
            f"#{incident.id} • {incident.category}",
            size=13,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
        ),
        ft.Text(
            f"{incident.severity} • {'Aberta' if is_open else 'Encerrada'}",
            size=11,
            weight=ft.FontWeight.BOLD,
            color=severity_color,
        ),
        ft.Text(
            f"Registrada por {incident.reported_by} em "
            f"{format_datetime(incident.reported_at, assume_utc=True)}",
            size=10,
            color=AppColors.TEXT_SECONDARY,
        ),
        ft.Text(incident.description, size=12, color=AppColors.TEXT_PRIMARY),
        ft.Text(
            f"Ação imediata: {incident.immediate_action}",
            size=11,
            color=AppColors.TEXT_SECONDARY,
        ),
    ]
    if incident.corrective_action:
        body.append(
            ft.Text(
                f"Ação corretiva: {incident.corrective_action}",
                size=11,
                color=AppColors.TEXT_SECONDARY,
            )
        )

    if is_open and callable(on_resolve):
        resolve_button = ft.Button(
            content="Registrar ação corretiva e encerrar",
            icon=ft.Icons.TASK_ALT,
        )

        def show_resolution(_event: object | None = None) -> None:
            page = resolve_button.page
            corrective = ft.TextField(
                label="Ação corretiva e verificação realizada",
                multiline=True,
                min_lines=3,
                max_lines=7,
                max_length=3000,
                bgcolor=AppColors.SURFACE,
                border_color=AppColors.DIVIDER,
                focused_border_color=AppColors.PRIMARY,
            )
            error = ft.Text("", size=11, color=AppColors.DANGER)

            def confirm(_confirm_event: object | None = None) -> None:
                value = corrective.value.strip()
                if len(value) < 15:
                    corrective.error = "Descreva o tratamento com pelo menos 15 caracteres."
                    _safe_update(corrective)
                    return
                result = on_resolve(incident.id, value)
                if result:
                    error.value = str(result)
                    _safe_update(error)
                    return
                page.pop_dialog()
                on_refresh()

            page.show_dialog(
                styled_dialog(
                    title=f"Encerrar falha #{incident.id}?",
                    subtitle="O registro original será preservado",
                    icon=ft.Icons.TASK_ALT,
                    content=ft.Column(
                        width=580,
                        tight=True,
                        spacing=12,
                        controls=[
                            dialog_banner(
                                "Registre a correção aplicada e como a eficácia foi verificada."
                            ),
                            corrective,
                            error,
                        ],
                    ),
                    actions=dialog_actions(
                        page=page,
                        primary_label="Encerrar falha",
                        primary_icon=ft.Icons.TASK_ALT,
                        on_confirm=confirm,
                    ),
                )
            )

        resolve_button.on_click = show_resolution
        body.append(resolve_button)

    return ft.Container(
        bgcolor=AppColors.PAGE_BACKGROUND,
        border=ft.Border.all(1, AppColors.DIVIDER),
        border_radius=12,
        padding=14,
        content=ft.Column(spacing=7, controls=body),
    )


def _safe_incident_panel(**kwargs) -> ft.Column:
    incidents = kwargs["system_incidents"]
    on_report = kwargs.get("on_report_system_incident")
    on_resolve = kwargs.get("on_resolve_system_incident")
    on_refresh = kwargs["on_refresh"]
    report_button = ft.Button(
        content="Registrar falha",
        icon=ft.Icons.BUG_REPORT_OUTLINED,
        bgcolor=AppColors.PRIMARY,
        color=AppColors.WHITE,
        visible=callable(on_report),
    )

    def show_report(_event: object | None = None) -> None:
        page = report_button.page
        selector = ft.Dropdown(
            label="Motivo da falha",
            value="software_crash",
            options=[
                ft.DropdownOption(key=item.code, text=item.label)
                for item in INCIDENT_REASONS
            ],
            bgcolor=AppColors.SURFACE,
            border_color=AppColors.DIVIDER,
            focused_border_color=AppColors.PRIMARY,
        )
        initial = incident_reason("software_crash")
        priority = ft.Text(
            f"Prioridade automática: {initial.severity}",
            size=12,
            weight=ft.FontWeight.BOLD,
            color=AppColors.DANGER,
        )
        guidance = ft.Text(initial.guidance, size=11, color=AppColors.TEXT_SECONDARY)
        description = ft.TextField(
            label="O que aconteceu?",
            multiline=True,
            min_lines=3,
            max_lines=5,
            max_length=2000,
            bgcolor=AppColors.SURFACE,
            border_color=AppColors.DIVIDER,
            focused_border_color=AppColors.PRIMARY,
        )
        immediate = ft.TextField(
            label="Qual ação você tomou ao reconhecer a falha?",
            multiline=True,
            min_lines=2,
            max_lines=4,
            max_length=2000,
            bgcolor=AppColors.SURFACE,
            border_color=AppColors.DIVIDER,
            focused_border_color=AppColors.PRIMARY,
        )
        error = ft.Text("", size=11, color=AppColors.DANGER)

        def update_priority(_change_event: object | None = None) -> None:
            selected = incident_reason(selector.value or "other")
            priority.value = f"Prioridade automática: {selected.severity}"
            priority.color = (
                AppColors.DANGER
                if selected.severity in {"Crítica", "Alta"}
                else AppColors.WARNING
            )
            guidance.value = selected.guidance
            _safe_update(priority)
            _safe_update(guidance)

        selector.on_select = update_priority

        def confirm(_confirm_event: object | None = None) -> None:
            description_value = description.value.strip()
            immediate_value = immediate.value.strip()
            if len(description_value) < 10:
                description.error = "Descreva a falha com pelo menos 10 caracteres."
                _safe_update(description)
                return
            if len(immediate_value) < 10:
                immediate.error = "Informe a ação imediata com pelo menos 10 caracteres."
                _safe_update(immediate)
                return
            result = on_report(
                selector.value or "other",
                description_value,
                immediate_value,
            )
            if result:
                error.value = str(result)
                _safe_update(error)
                return
            page.pop_dialog()
            on_refresh()

        page.show_dialog(
            styled_dialog(
                title="Registrar falha do sistema",
                subtitle="Evidência para avaliação de impacto e ação corretiva",
                icon=ft.Icons.BUG_REPORT_OUTLINED,
                content=ft.Column(
                    width=610,
                    tight=True,
                    spacing=11,
                    controls=[
                        dialog_banner(
                            "Registre o impacto observado e a contenção adotada."
                        ),
                        selector,
                        ft.Container(
                            border_radius=11,
                            bgcolor=AppColors.WARNING_LIGHT,
                            padding=11,
                            content=ft.Column(
                                spacing=3,
                                controls=[priority, guidance],
                            ),
                        ),
                        description,
                        immediate,
                        error,
                    ],
                ),
                actions=dialog_actions(
                    page=page,
                    primary_label="Salvar registro",
                    primary_icon=ft.Icons.SAVE_OUTLINED,
                    on_confirm=confirm,
                ),
            )
        )

    report_button.on_click = show_report
    cards = [
        _incident_card(
            incident,
            on_resolve=on_resolve,
            on_refresh=on_refresh,
        )
        for incident in incidents
    ]
    if not cards:
        cards = [
            ft.Container(
                bgcolor=AppColors.PAGE_BACKGROUND,
                border=ft.Border.all(1, AppColors.DIVIDER),
                border_radius=12,
                padding=14,
                content=ft.Text(
                    "Nenhuma falha registrada.",
                    size=11,
                    color=AppColors.TEXT_SECONDARY,
                ),
            )
        ]
    return ft.Column(
        spacing=12,
        controls=[
            ft.Row(
                wrap=True,
                run_spacing=8,
                spacing=12,
                controls=[
                    ft.Column(
                        spacing=3,
                        controls=[
                            ft.Text(
                                "Falhas do sistema e ações corretivas",
                                size=17,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                            ft.Text(
                                "Registre, avalie o impacto e demonstre o tratamento adotado.",
                                size=12,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                        ],
                    ),
                    report_button,
                ],
            ),
            dialog_banner(
                "Relacionado à ABNT NBR ISO/IEC 17025:2017, itens 7.10, 7.11.3 e 8.7. "
                "O registro no software não substitui o procedimento do laboratório."
            ),
            *cards,
        ],
    )


def _safe_settings_builder(**kwargs) -> ft.Control:
    current_user = kwargs["current_user"]
    content = production_settings_module.build_settings_view(
        database_path=kwargs["database_path"],
        backup_directory=kwargs["backup_directory"],
        notifications_enabled=kwargs["notifications_enabled"],
        notification_status=kwargs["notification_status"],
        email_settings=kwargs["email_settings"],
        email_recipients=kwargs["email_recipients"],
        system_incidents=kwargs["system_incidents"],
        theme_mode=kwargs["theme_mode"],
        current_user=current_user,
        on_theme_change=kwargs["on_theme_change"],
        on_change_password=kwargs["on_change_password"],
        on_manage_users=kwargs["on_manage_users"],
        on_help=kwargs["on_help"],
        on_enable_notifications=kwargs["on_enable_notifications"],
        on_disable_notifications=kwargs["on_disable_notifications"],
        on_test_notification=kwargs["on_test_notification"],
        on_save_email_settings=kwargs["on_save_email_settings"],
        on_test_email=kwargs["on_test_email"],
        on_select_profile_photo=kwargs["on_select_profile_photo"],
        on_remove_profile_photo=kwargs["on_remove_profile_photo"],
        on_open_data_folder=kwargs["on_open_data_folder"],
        on_backup=kwargs["on_backup"],
        on_configure_backup=kwargs["on_configure_backup"],
        on_report_system_incident=(
            kwargs["on_report_system_incident"]
            or (lambda *_args: "Perfil somente leitura.")
        ),
        on_resolve_system_incident=kwargs["on_resolve_system_incident"],
        on_refresh=kwargs["on_refresh"],
        on_rotate_administrator_recovery=kwargs.get(
            "on_rotate_administrator_recovery"
        ),
        allow_theme_change=True,
        managed_server_mode=True,
    )

    content.controls = [
        control
        for control in content.controls
        if not any(
            isinstance(child, ft.Text)
            and child.value == "A escolha fica salva neste computador."
            for child in _walk(control)
        )
    ]
    for control in _walk(content):
        if isinstance(control, ft.Switch) and control.label == "Usar tema escuro":
            control.visible = False
        if isinstance(control, ft.Button):
            label = _button_label(control)
            if label == "Desativar avisos":
                control.disabled = not kwargs["notifications_enabled"]
            elif label == "Ativar avisos":
                control.disabled = kwargs["notifications_enabled"]
            elif label == "Testar notificação":
                control.disabled = False

    content.controls.insert(
        2,
        production_settings_module._theme_card(
            kwargs["theme_mode"], kwargs["on_theme_change"]
        ),
    )
    content.controls.insert(
        3,
        build_server_status_card(
            kwargs["identity"],
            backup_directory=kwargs["backup_directory"],
            is_admin=current_user.is_admin,
            on_configure_backup=kwargs["on_configure_backup"],
        ),
    )

    incident_target = next(
        (
            control
            for control in content.controls
            if any(
                isinstance(child, ft.Text)
                and child.value == "Falhas do sistema e ações corretivas"
                for child in _walk(control)
            )
        ),
        None,
    )
    if isinstance(incident_target, ft.Container):
        incident_target.content = _safe_incident_panel(**kwargs)

    return apply_interaction_polish(content)


_App = production_app.ProductionClimateTestApplication
_original_refresh_shell_frame = getattr(_App, "_refresh_shell_frame", None)


def _refresh_notification_badge(self) -> None:
    """Atualiza apenas o badge; nunca remonta a tela aberta em segundo plano."""

    if self._screen_container is None:
        return
    try:
        count = sum(
            not item.is_read
            for item in self._production_repository.list_user_notifications(
                user_id=self._current_user.id,
                is_admin=self._current_user.is_admin,
            )
        )
    except (OSError, RuntimeError, ValueError):
        return

    root = self._screen_container.content
    if not isinstance(root, ft.Control):
        return
    target = next(
        (
            control
            for control in _walk(root)
            if isinstance(control, ft.Container)
            and (
                control.tooltip == "Notificações"
                or any(
                    isinstance(child, ft.Text) and child.value == "Notificações"
                    for child in _walk(control)
                    if child is not control
                )
            )
        ),
        None,
    )
    if not isinstance(target, ft.Container):
        if callable(_original_refresh_shell_frame):
            _original_refresh_shell_frame(self)
        return
    target.badge = (
        ft.Badge(
            label=str(min(count, 99)),
            bgcolor=AppColors.DANGER,
            text_color=AppColors.WHITE,
        )
        if count
        else None
    )
    _safe_update(target)


def _show_new_test(self) -> None:
    if not self._current_user.can_operate:
        self._show_message("Este perfil possui acesso somente para consulta.", error=True)
        return
    if self._selected_view == "new_test" and self._new_test_view is not None:
        return
    self._prepare_theme()
    view = SafeNewTestView(
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
    view = SafeNewTestView(
        on_cancel=lambda: self.show_details(test_id),
        on_save=lambda command: self._update_test(test_id, command),
        details=self._service.get_details(test_id),
    )
    view.save_button.disabled = False
    self._render(view.root, selected_view="details")
    self._page.run_task(_force_scroll_top, view.root)


def _show_details(self, test_id: int) -> None:
    self._prepare_theme()
    self._active_test_id = test_id
    details = self._service.get_details(test_id)
    view = TestDetailsView(
        details,
        on_back=self.show_tests,
        on_start_chamber=lambda value: self._perform(
            test_id,
            lambda: self._service.start_chamber(test_id, value),
            "Câmara iniciada e prazos calculados.",
        ),
        on_start_drying=lambda value: self._perform(
            test_id,
            lambda: self._service.start_drying(test_id, value),
            "Secagem iniciada a partir do horário real.",
        ),
        on_finish=lambda value: self._perform(
            test_id,
            lambda: self._service.finish(test_id, value),
            "Ensaio finalizado.",
        ),
        on_cancel=lambda reason: self._perform(
            test_id,
            lambda: self._service.cancel(test_id, reason),
            "Ensaio cancelado e motivo registrado.",
        ),
        on_edit=lambda: self.show_edit_test(test_id),
        on_delete=lambda: self._delete_test(test_id),
        on_change_timestamp=lambda timestamp, value, reason: self._perform(
            test_id,
            lambda: self._service.change_operational_timestamp(
                test_id, timestamp, value, reason
            ),
            "Horário operacional corrigido e alteração registrada.",
        ),
        on_advance_for_testing=(
            (
                lambda: self._perform(
                    test_id,
                    lambda: self._service.advance_for_testing(test_id),
                    "Etapa avançada somente para validação.",
                )
            )
            if production_app.test_controls_enabled()
            else None
        ),
    )
    if self._current_user.is_viewer:
        _disable_viewer_actions(view.root)
    if self._current_user.is_admin:
        view.root.controls.insert(
            1,
            ft.Container(
                bgcolor=AppColors.DANGER_LIGHT,
                border=ft.Border.all(1, AppColors.DANGER),
                border_radius=12,
                padding=12,
                content=ft.Row(
                    wrap=True,
                    run_spacing=8,
                    controls=[
                        ft.Text(
                            "Administração: exclusão permanente disponível para cadastros "
                            "fictícios, duplicados ou inválidos.",
                            size=11,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                        ft.Button(
                            content="Excluir do histórico",
                            icon=ft.Icons.DELETE_OUTLINE,
                            color=AppColors.DANGER,
                            on_click=lambda _event: _show_admin_delete_dialog(
                                self, test_id
                            ),
                        ),
                    ],
                ),
            ),
        )
    view.root.key = f"safe-details-{test_id}-{id(view)}"
    self._render(view.root, selected_view="details")
    self._page.run_task(_force_scroll_top, view.root)


def install_round4_fixes() -> None:
    if getattr(production_app, "_round4_fixes_installed", False):
        return
    _App._refresh_shell_frame = _refresh_notification_badge
    _App.show_new_test = _show_new_test
    _App.show_edit_test = _show_edit_test
    _App.show_details = _show_details
    production_app.build_production_settings_view = _safe_settings_builder
    production_settings_module.build_production_settings_view = _safe_settings_builder
    production_app._round4_fixes_installed = True


install_round4_fixes()
main = production_app.main
