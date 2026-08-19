"""Integração funcional da v0.8.6 para validação controlada.

A camada é instalada depois da estabilização v0.8.5. Ela preserva o fluxo legado
para ensaios sem ``thermal_cold_workflows`` e acrescenta somente o comportamento
explicitamente habilitado pelo operador.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import replace
from datetime import datetime

import flet as ft

from climatetest_manager import production_app, round7_runtime
from climatetest_manager.domain.cold_flow import (
    cold_temperature_range,
    parse_minimum_ambient_service_temperature,
)
from climatetest_manager.domain.enums import DeadlineCondition, TestSituation
from climatetest_manager.services.climate_tests import ClimateTestService, DashboardSummary
from climatetest_manager.services.cold_workflows import (
    ColdWorkflowError,
    ColdWorkflowService,
    ColdWorkflowSnapshot,
)
from climatetest_manager.services.scheduling import classify_deadline
from climatetest_manager.ui.formatters import format_datetime, format_decimal
from climatetest_manager.ui.theme import AppColors
from climatetest_manager.ui.views.final_new_test import FinalNewTestView
from climatetest_manager.ui.views.new_test import NewTestDraft

_ORIGINAL_FINISH = ClimateTestService.finish
_ORIGINAL_LIST_TESTS = ClimateTestService.list_tests
_ORIGINAL_DASHBOARD_SUMMARY = ClimateTestService.dashboard_summary
_ORIGINAL_START = production_app.ProductionClimateTestApplication.start


def _service_from_repository(
    repository, *, actor_provider=lambda: "Não identificado"
) -> ColdWorkflowService:
    return ColdWorkflowService(
        repository._session_factory,
        actor_provider=actor_provider,
    )


def _service_for_app(app: production_app.ProductionClimateTestApplication) -> ColdWorkflowService:
    return _service_from_repository(
        app._repository,
        actor_provider=lambda: app._current_user.actor_label,
    )


def _service_for_climate(service: ClimateTestService) -> ColdWorkflowService:
    return _service_from_repository(
        service._repository,
        actor_provider=service._actor,
    )


def _finish_with_optional_cold(
    self: ClimateTestService,
    test_id: int,
    finished_at: datetime | None = None,
) -> None:
    workflow = _service_for_climate(self).get(test_id)
    if workflow is not None and workflow.cold_planned and workflow.cold_started_at is None:
        _service_for_climate(self).complete_heat(test_id, finished_at)
        return
    _ORIGINAL_FINISH(self, test_id, finished_at)


def _list_tests_with_cold(self: ClimateTestService):
    items = _ORIGINAL_LIST_TESTS(self)
    cold_service = _service_for_climate(self)
    now = self._now_provider().replace(microsecond=0)
    result = []
    for item in items:
        workflow = cold_service.get(item.id)
        if workflow is None:
            result.append(item)
            continue
        situation = item.situation
        nominal = item.nominal_end_at
        maximum = item.maximum_end_at
        deadline = item.deadline_condition
        progress = item.progress_percent
        progress_label = item.progress_label

        if situation == TestSituation.AWAITING_CONDITIONING.value:
            nominal = maximum = None
            deadline = None
            progress = 0.0
            progress_label = "Aguardando início do acondicionamento"
        elif situation == TestSituation.CONDITIONING.value:
            nominal = workflow.conditioning_nominal_end_at
            maximum = workflow.conditioning_maximum_end_at
            if nominal is not None and maximum is not None:
                deadline = classify_deadline(now, nominal, maximum).value
                if workflow.conditioning_started_at is not None:
                    elapsed = max((now - workflow.conditioning_started_at).total_seconds(), 0)
                    progress = min(elapsed / (24 * 3600), 1.0)
                if now < nominal:
                    progress_label = "Acondicionamento em andamento"
                elif now <= maximum:
                    progress_label = "Mínimo de 24 h concluído • frio disponível"
                else:
                    progress_label = "Limite de 72 h ultrapassado"
        elif situation == TestSituation.IN_COLD.value:
            nominal = workflow.cold_nominal_end_at
            maximum = workflow.cold_maximum_end_at
            if nominal is not None and maximum is not None:
                deadline = classify_deadline(now, nominal, maximum).value
                if workflow.cold_started_at is not None:
                    elapsed = max((now - workflow.cold_started_at).total_seconds(), 0)
                    progress = min(elapsed / (24 * 3600), 1.0)
                if now < nominal:
                    progress_label = "Frio em andamento"
                elif now <= maximum:
                    progress_label = "24 h concluídas • retirar até o limite"
                else:
                    progress_label = "Limite de 26 h ultrapassado"

        result.append(
            replace(
                item,
                nominal_end_at=nominal,
                maximum_end_at=maximum,
                deadline_condition=deadline,
                progress_percent=progress,
                progress_label=progress_label,
            )
        )
    return result


def _dashboard_summary_with_cold(self: ClimateTestService) -> DashboardSummary:
    items = self.list_tests()
    active = {
        TestSituation.IN_CHAMBER.value,
        TestSituation.DRYING.value,
        TestSituation.AWAITING_CONDITIONING.value,
        TestSituation.CONDITIONING.value,
        TestSituation.IN_COLD.value,
    }
    return DashboardSummary(
        in_progress=sum(item.situation in active and not item.is_paused for item in items),
        overdue=sum(item.deadline_condition == DeadlineCondition.OVERDUE.value for item in items),
        due_today=sum(
            item.deadline_condition == DeadlineCondition.DUE_TODAY.value for item in items
        ),
        drying=sum(item.situation == TestSituation.DRYING.value for item in items),
        in_tolerance=sum(
            item.deadline_condition == DeadlineCondition.IN_TOLERANCE.value for item in items
        ),
        waiting=sum(item.situation == TestSituation.WAITING.value for item in items),
        paused=sum(item.is_paused for item in items),
    )


def _normalize_negative(value: str) -> str:
    raw = value.replace(".", ",")
    result = []
    for index, character in enumerate(raw):
        if character.isdigit() or character == "," or (character == "-" and index == 0):
            result.append(character)
    normalized = "".join(result)
    if normalized.count(",") > 1:
        first = normalized.find(",")
        normalized = normalized[: first + 1] + normalized[first + 1 :].replace(",", "")
    return normalized[:10]


class V086NewTestView(FinalNewTestView):
    """Cadastro v0.8.6 com planejamento opcional do item 26.9."""

    def __init__(self, *args, cold_snapshot: ColdWorkflowSnapshot | None = None, **kwargs) -> None:
        requested_on_save = kwargs.pop("on_save")
        self._v086_requested_on_save = requested_on_save
        self._v086_cold_snapshot = cold_snapshot
        self.cold_planned = ft.Switch(
            label="Realizar resistência térmica ao frio — 26.9",
            value=bool(cold_snapshot and cold_snapshot.cold_planned),
        )
        self.minimum_ambient_service_temperature = ft.TextField(
            label="Temperatura mínima ambiente de serviço (°C)",
            hint_text="Em branco: -20 °C",
            value=(
                str(cold_snapshot.minimum_ambient_service_temperature_c).replace(".", ",")
                if cold_snapshot is not None
                else ""
            ),
            border_radius=10,
            border_color=AppColors.DIVIDER,
            focused_border_color=AppColors.PRIMARY,
            bgcolor=AppColors.SURFACE,
        )
        self._cold_preview = ft.Text("", size=10, color=AppColors.TEXT_SECONDARY)
        self._cold_fields = ft.Container(visible=bool(self.cold_planned.value))
        self._cold_panel_control: ft.Container | None = None

        def save_wrapper(command) -> None:
            requested_on_save(
                command,
                bool(self.cold_planned.value),
                self.minimum_ambient_service_temperature.value,
            )

        kwargs["on_save"] = save_wrapper
        super().__init__(*args, **kwargs)
        locked = bool(
            cold_snapshot
            and (
                cold_snapshot.conditioning_started_at is not None
                or cold_snapshot.cold_started_at is not None
            )
        )
        self.cold_planned.disabled = locked
        self.minimum_ambient_service_temperature.disabled = locked
        self.cold_planned.on_change = self._on_cold_change
        self.minimum_ambient_service_temperature.on_change = self._on_cold_temperature_change
        self._refresh_cold_preview()

    def _cold_panel(self) -> ft.Container:
        self._cold_fields.content = ft.Column(
            spacing=7,
            controls=[
                self.minimum_ambient_service_temperature,
                self._cold_preview,
                ft.Text(
                    "O acondicionamento pós-calor será controlado por 24 a 72 h. "
                    "Depois, o frio será controlado por 24 a 26 h.",
                    size=9,
                    color=AppColors.TEXT_SECONDARY,
                ),
            ],
        )
        panel = ft.Container(
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(1, AppColors.DIVIDER),
            border_radius=14,
            padding=12,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        spacing=9,
                        controls=[
                            ft.Container(
                                width=32,
                                height=32,
                                border_radius=9,
                                bgcolor=AppColors.PRIMARY_LIGHT,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(ft.Icons.AC_UNIT, size=17, color=AppColors.PRIMARY),
                            ),
                            ft.Column(
                                expand=True,
                                spacing=1,
                                controls=[
                                    ft.Text(
                                        "Etapa posterior ao calor",
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color=AppColors.TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        "Planejamento opcional de acondicionamento e frio.",
                                        size=9,
                                        color=AppColors.TEXT_SECONDARY,
                                    ),
                                ],
                            ),
                        ],
                    ),
                    self.cold_planned,
                    self._cold_fields,
                ],
            ),
        )
        self._cold_panel_control = panel
        return panel

    def _build(self) -> ft.Column:
        root = super()._build()
        # Cabeçalho, erro, painéis superiores, [novo fluxo], observações...
        root.controls.insert(3, self._cold_panel())
        return root

    def _on_cold_change(self, _event: object | None = None) -> None:
        self._cold_fields.visible = bool(self.cold_planned.value)
        self._refresh_cold_preview()
        with suppress(RuntimeError):
            if self._cold_panel_control is not None:
                self._cold_panel_control.update()

    def _on_cold_temperature_change(self, _event: object | None = None) -> None:
        self.minimum_ambient_service_temperature.value = _normalize_negative(
            self.minimum_ambient_service_temperature.value
        )
        self._refresh_cold_preview()
        with suppress(RuntimeError):
            self.minimum_ambient_service_temperature.update()
            self._cold_preview.update()

    def _refresh_cold_preview(self) -> None:
        try:
            minimum = parse_minimum_ambient_service_temperature(
                self.minimum_ambient_service_temperature.value
            )
            interval = cold_temperature_range(minimum)
            self._cold_preview.value = (
                f"Faixa calculada para o frio: {format_decimal(interval.minimum_c)} °C a "
                f"{format_decimal(interval.maximum_c)} °C • 24 a 26 h"
            )
            self.minimum_ambient_service_temperature.error = None
        except ValueError as error:
            self._cold_preview.value = "Revise a temperatura informada."
            self.minimum_ambient_service_temperature.error = str(error)

    def snapshot_draft(self) -> NewTestDraft:
        base = super().snapshot_draft()
        return NewTestDraft(
            {
                **base.values,
                "cold_planned": bool(self.cold_planned.value),
                "minimum_ambient_service_temperature": self.minimum_ambient_service_temperature.value,
            }
        )

    def restore_draft(self, draft: NewTestDraft) -> None:
        super().restore_draft(draft)
        self.cold_planned.value = bool(draft.values.get("cold_planned", False))
        value = draft.values.get("minimum_ambient_service_temperature")
        if isinstance(value, str):
            self.minimum_ambient_service_temperature.value = value
        self._cold_fields.visible = bool(self.cold_planned.value)
        self._refresh_cold_preview()


def _save_test_with_cold(app, command, planned: bool, minimum_temperature: str) -> None:
    if planned:
        # Valida antes de gravar o cadastro para não deixar registro parcial.
        parse_minimum_ambient_service_temperature(minimum_temperature)
    test_id = app._service.create(command)
    if planned:
        _service_for_app(app).plan(test_id, minimum_temperature)
    app._new_test_view = None
    app._new_test_draft = None
    app.show_dashboard()
    app._page.show_dialog(
        ft.SnackBar(
            content=f"Ensaio #{test_id} cadastrado com sucesso.",
            bgcolor=AppColors.PRIMARY,
            show_close_icon=True,
        )
    )


def _update_test_with_cold(
    app, test_id: int, command, planned: bool, minimum_temperature: str
) -> None:
    try:
        if planned:
            parse_minimum_ambient_service_temperature(minimum_temperature)
        app._service.update(test_id, command)
        cold = _service_for_app(app)
        existing = cold.get(test_id)
        if planned:
            if existing is None or (
                existing.conditioning_started_at is None and existing.cold_started_at is None
            ):
                cold.plan(test_id, minimum_temperature)
        elif existing is not None:
            cold.remove_plan(test_id, reason="Frio removido durante revisão do cadastro")
    except (ValueError, LookupError) as error:
        app._show_message(str(error), error=True)
        return
    app.show_details(test_id)
    app._show_message("Dados corrigidos e alteração registrada.")


def _show_new_test(self: production_app.ProductionClimateTestApplication) -> None:
    if not self._current_user.can_operate:
        self._show_message("Este perfil possui acesso somente para consulta.", error=True)
        return
    if self._selected_view == "new_test" and self._new_test_view is not None:
        return
    self._prepare_theme()
    view = V086NewTestView(
        on_cancel=self._confirm_discard_new_test,
        on_save=lambda command, planned, temperature: _save_test_with_cold(
            self, command, planned, temperature
        ),
        draft=self._new_test_draft,
    )
    view.save_button.disabled = False
    self._new_test_view = view
    self._render(view.root, selected_view="new_test")


def _show_edit_test(self: production_app.ProductionClimateTestApplication, test_id: int) -> None:
    if not self._current_user.can_operate:
        self._show_message("Este perfil possui acesso somente para consulta.", error=True)
        return
    self._prepare_theme()
    cold = _service_for_app(self).get(test_id)
    view = V086NewTestView(
        on_cancel=lambda: self.show_details(test_id),
        on_save=lambda command, planned, temperature: _update_test_with_cold(
            self, test_id, command, planned, temperature
        ),
        details=self._service.get_details(test_id),
        cold_snapshot=cold,
    )
    view.save_button.disabled = False
    self._render(view.root, selected_view="details")


def _phase_card(title: str, icon, lines: list[str], *, emphasis: bool = False) -> ft.Container:
    return ft.Container(
        border_radius=12,
        bgcolor=AppColors.PRIMARY_LIGHT if emphasis else AppColors.PAGE_BACKGROUND,
        border=ft.Border.all(1, AppColors.DIVIDER),
        padding=11,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Row(
                    spacing=7,
                    controls=[
                        ft.Icon(icon, size=17, color=AppColors.PRIMARY),
                        ft.Text(
                            title,
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                    ],
                ),
                *[ft.Text(line, size=9, color=AppColors.TEXT_SECONDARY) for line in lines],
            ],
        ),
    )


class V086DetailsView(round7_runtime.CleanDetailsView):
    def __init__(self, *args, cold_snapshot: ColdWorkflowSnapshot | None = None, **kwargs) -> None:
        self._v086_cold = cold_snapshot
        self._v086_start_conditioning = kwargs.pop("on_start_conditioning")
        self._v086_start_cold = kwargs.pop("on_start_cold")
        self._v086_finish_cold = kwargs.pop("on_finish_cold")
        self._v086_skip_cold = kwargs.pop("on_skip_cold")
        super().__init__(*args, **kwargs)

    def _phase_panel(self):
        base = super()._phase_panel()
        # A v0.8.5 já cria os cards corretos, mas os empilhava. Reorganiza em
        # grade responsiva sem reconstruir o conteúdo interno.
        try:
            controls = list(base.content.controls)
            if len(controls) >= 2:
                heading = controls[0]
                cards = controls[1:]
                row = ft.ResponsiveRow(
                    spacing=9,
                    run_spacing=9,
                    controls=[
                        ft.Container(col={"xs": 12, "md": 6}, content=card) for card in cards
                    ],
                )
                base.content.controls = [heading, row]
        except (AttributeError, TypeError):
            row = None

        workflow = self._v086_cold
        if workflow is None or not workflow.cold_planned:
            return base

        conditioning_lines = [
            "20 ± 5 °C • 50 ± 10 % UR • 24 a 72 h",
            f"Início: {format_datetime(workflow.conditioning_started_at)}",
            f"Mínimo: {format_datetime(workflow.conditioning_nominal_end_at)}",
            f"Limite: {format_datetime(workflow.conditioning_maximum_end_at)}",
        ]
        cold_lines = [
            (
                f"{format_decimal(workflow.temperature_range.minimum_c)} °C a "
                f"{format_decimal(workflow.temperature_range.maximum_c)} °C • 24 a 26 h"
            ),
            f"Entrada: {format_datetime(workflow.cold_started_at)}",
            f"Retirada nominal: {format_datetime(workflow.cold_nominal_end_at)}",
            f"Limite: {format_datetime(workflow.cold_maximum_end_at)}",
        ]
        conditioning = _phase_card(
            "Acondicionamento pós-calor",
            ft.Icons.HOURGLASS_BOTTOM,
            conditioning_lines,
            emphasis=self._details.situation == TestSituation.CONDITIONING.value,
        )
        cold = _phase_card(
            "Resistência térmica ao frio — 26.9",
            ft.Icons.AC_UNIT,
            cold_lines,
            emphasis=self._details.situation == TestSituation.IN_COLD.value,
        )
        try:
            row.controls.extend(
                [
                    ft.Container(col={"xs": 12, "md": 6}, content=conditioning),
                    ft.Container(col={"xs": 12, "md": 6}, content=cold),
                ]
            )
            return base
        except (AttributeError, UnboundLocalError):
            return ft.Column(spacing=9, controls=[base, conditioning, cold])

    def _time_dialog(self, title: str, callback) -> None:
        page = self.root.page
        manual = ft.TextField(
            label="Data e hora real",
            hint_text="DD/MM/AAAA HH:MM",
            value=datetime.now().strftime("%d/%m/%Y %H:%M"),
            width=330,
        )
        error = ft.Text("", size=10, color=AppColors.DANGER)

        def use_now(_event=None) -> None:
            page.pop_dialog()
            callback(None)

        def use_manual(_event=None) -> None:
            try:
                value = datetime.strptime(manual.value.strip(), "%d/%m/%Y %H:%M")
            except ValueError:
                error.value = "Use o formato DD/MM/AAAA HH:MM."
                with suppress(RuntimeError):
                    error.update()
                return
            page.pop_dialog()
            callback(value)

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(title, weight=ft.FontWeight.BOLD),
                content=ft.Column(
                    width=430,
                    tight=True,
                    spacing=10,
                    controls=[
                        ft.Text(
                            "Use o horário atual ou registre o momento real manualmente.",
                            size=11,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        manual,
                        error,
                    ],
                ),
                actions=[
                    ft.TextButton(content="Cancelar", on_click=lambda _e: page.pop_dialog()),
                    ft.Button(content="Usar agora", icon=ft.Icons.SCHEDULE, on_click=use_now),
                    ft.Button(
                        content="Usar horário informado",
                        icon=ft.Icons.EDIT_CALENDAR,
                        bgcolor=AppColors.PRIMARY,
                        color=AppColors.WHITE,
                        on_click=use_manual,
                    ),
                ],
            )
        )

    def _skip_dialog(self) -> None:
        page = self.root.page
        reason = ft.TextField(
            label="Justificativa *",
            hint_text="Informe por que o ensaio de frio não será realizado.",
            multiline=True,
            min_lines=2,
            max_lines=4,
            max_length=500,
        )

        def confirm(_event=None) -> None:
            if len(reason.value.strip()) < 8:
                reason.error = "Informe uma justificativa com pelo menos 8 caracteres."
                with suppress(RuntimeError):
                    reason.update()
                return
            page.pop_dialog()
            self._v086_skip_cold(reason.value.strip())

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Não realizar resistência térmica ao frio"),
                content=ft.Column(width=470, tight=True, controls=[reason]),
                actions=[
                    ft.TextButton(content="Voltar", on_click=lambda _e: page.pop_dialog()),
                    ft.Button(content="Confirmar", on_click=confirm),
                ],
            )
        )

    def _action_panel(self):
        base = super()._action_panel()
        workflow = self._v086_cold
        if workflow is None or not workflow.cold_planned or not self._r7_can_operate:
            return base
        controls = [base]
        situation = self._details.situation
        if situation == TestSituation.AWAITING_CONDITIONING.value:
            controls.append(
                ft.Container(
                    border=ft.Border.all(1, AppColors.DIVIDER),
                    border_radius=12,
                    padding=12,
                    content=ft.Row(
                        wrap=True,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                "Próxima etapa: acondicionamento pós-calor",
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Button(
                                        content="Iniciar acondicionamento",
                                        icon=ft.Icons.HOURGLASS_BOTTOM,
                                        bgcolor=AppColors.PRIMARY,
                                        color=AppColors.WHITE,
                                        on_click=lambda _e: self._time_dialog(
                                            "Iniciar acondicionamento",
                                            self._v086_start_conditioning,
                                        ),
                                    ),
                                    ft.TextButton(
                                        content="Não realizar frio",
                                        on_click=lambda _e: self._skip_dialog(),
                                    ),
                                ]
                            ),
                        ],
                    ),
                )
            )
        elif situation == TestSituation.CONDITIONING.value:
            ready = bool(
                workflow.conditioning_nominal_end_at
                and datetime.now().replace(microsecond=0) >= workflow.conditioning_nominal_end_at
            )
            controls.append(
                ft.Container(
                    border=ft.Border.all(1, AppColors.DIVIDER),
                    border_radius=12,
                    padding=12,
                    content=ft.Row(
                        wrap=True,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                "Acondicionamento mínimo concluído"
                                if ready
                                else "Acondicionamento em andamento",
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Button(
                                        content="Iniciar frio",
                                        icon=ft.Icons.AC_UNIT,
                                        disabled=not ready,
                                        tooltip=(
                                            None
                                            if ready
                                            else "Disponível após completar 24 h de acondicionamento."
                                        ),
                                        bgcolor=AppColors.PRIMARY if ready else None,
                                        color=AppColors.WHITE if ready else None,
                                        on_click=(
                                            lambda _e: (
                                                self._time_dialog(
                                                    "Iniciar resistência térmica ao frio",
                                                    self._v086_start_cold,
                                                )
                                                if ready
                                                else None
                                            )
                                        ),
                                    ),
                                    ft.TextButton(
                                        content="Não realizar frio",
                                        on_click=lambda _e: self._skip_dialog(),
                                    ),
                                ]
                            ),
                        ],
                    ),
                )
            )
        elif situation == TestSituation.IN_COLD.value:
            controls.append(
                ft.Container(
                    border=ft.Border.all(1, AppColors.DIVIDER),
                    border_radius=12,
                    padding=12,
                    content=ft.Row(
                        wrap=True,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                "Resistência térmica ao frio em andamento",
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Button(
                                content="Registrar retirada do frio",
                                icon=ft.Icons.LOGOUT,
                                bgcolor=AppColors.PRIMARY,
                                color=AppColors.WHITE,
                                on_click=lambda _e: self._time_dialog(
                                    "Registrar retirada do frio",
                                    self._v086_finish_cold,
                                ),
                            ),
                        ],
                    ),
                )
            )
        return ft.Column(spacing=9, controls=controls)


def _cold_perform(app, test_id: int, operation, success: str) -> None:
    try:
        operation()
    except (ColdWorkflowError, ValueError, LookupError) as error:
        app._show_message(str(error), error=True)
        return
    app.show_details(test_id)
    app._show_message(success)


def _show_details(self: production_app.ProductionClimateTestApplication, test_id: int) -> None:
    self._prepare_theme()
    self._active_test_id = test_id
    details = self._service.get_details(test_id)
    cold_service = _service_for_app(self)
    workflow = cold_service.get(test_id)
    view = V086DetailsView(
        details,
        cold_snapshot=workflow,
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
            (
                "Resistência térmica ao calor finalizada. Inicie o acondicionamento."
                if workflow is not None and workflow.cold_planned
                else "Ensaio finalizado."
            ),
        ),
        on_start_conditioning=lambda value: _cold_perform(
            self,
            test_id,
            lambda: cold_service.start_conditioning(test_id, value),
            "Acondicionamento iniciado e janela de 24 a 72 h calculada.",
        ),
        on_start_cold=lambda value: _cold_perform(
            self,
            test_id,
            lambda: cold_service.start_cold(test_id, value),
            "Ensaio de frio iniciado. Alertas de retirada foram agendados.",
        ),
        on_finish_cold=lambda value: _cold_perform(
            self,
            test_id,
            lambda: cold_service.finish_cold(test_id, value),
            "Retirada do frio registrada e ensaio finalizado.",
        ),
        on_skip_cold=lambda reason: _cold_perform(
            self,
            test_id,
            lambda: cold_service.skip_cold(test_id, reason),
            "Ensaio de frio marcado como não realizado com justificativa.",
        ),
        on_cancel=lambda reason: self._perform(
            test_id,
            lambda: self._service.cancel(test_id, reason),
            "Ensaio cancelado e motivo registrado.",
        ),
        on_edit=lambda: self.show_edit_test(test_id),
        on_delete=lambda: self._delete_test(test_id),
        on_admin_delete=lambda reason: self._delete_test_as_admin(test_id, reason),
        is_admin=self._current_user.is_admin,
        can_operate=self._current_user.can_operate,
        on_change_timestamp=lambda timestamp, value, reason: self._perform(
            test_id,
            lambda: self._service.change_operational_timestamp(test_id, timestamp, value, reason),
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
    self._render(view.root, selected_view="details")


async def _dashboard_sync_loop(app: production_app.ProductionClimateTestApplication) -> None:
    """Atualiza a Dashboard quando outra estação altera o banco central."""

    while getattr(app, "_v086_sync_active", False):
        await asyncio.sleep(5)
        if not getattr(app, "_v086_sync_active", False):
            return
        if getattr(app, "_selected_view", None) != "dashboard":
            continue
        if getattr(app, "_v086_sync_refreshing", False):
            continue
        app._v086_sync_refreshing = True
        try:
            app.show_dashboard()
        except (OSError, RuntimeError, ValueError):
            pass
        finally:
            app._v086_sync_refreshing = False


def _start_with_sync(self: production_app.ProductionClimateTestApplication) -> None:
    self._v086_sync_active = True
    _ORIGINAL_START(self)
    self._page.run_task(_dashboard_sync_loop, self)


def install() -> None:
    if getattr(production_app, "_v086_runtime_installed", False):
        return
    ClimateTestService.finish = _finish_with_optional_cold
    ClimateTestService.list_tests = _list_tests_with_cold
    ClimateTestService.dashboard_summary = _dashboard_summary_with_cold
    app = production_app.ProductionClimateTestApplication
    app.show_new_test = _show_new_test
    app.show_edit_test = _show_edit_test
    app.show_details = _show_details
    app.start = _start_with_sync
    production_app._v086_runtime_installed = True
