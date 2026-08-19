"""Ajustes do beta v0.8.6 para tornar o acondicionamento independente do frio.

Ensaios novos da v0.8.6 sempre recebem o fluxo pós-calor. O frio continua
opcional. Ensaios legados, sem registro em ``thermal_cold_workflows``, mantêm o
comportamento da v0.8.5 até que o operador ative explicitamente o fluxo novo.
"""

from __future__ import annotations

from datetime import datetime

import flet as ft
from sqlalchemy import select

from climatetest_manager import production_app, v086_runtime
from climatetest_manager.database.cold_models import ThermalColdWorkflowRecord
from climatetest_manager.database.models import ClimateTestRecord
from climatetest_manager.domain.cold_flow import (
    conditioning_window,
    parse_minimum_ambient_service_temperature,
)
from climatetest_manager.domain.enums import TestSituation
from climatetest_manager.services.climate_tests import ClimateTestService
from climatetest_manager.services.cold_workflows import (
    STATUS_AWAITING_CONDITIONING,
    STATUS_COMPLETED,
    STATUS_COMPLETED_LATE,
    STATUS_CONDITIONING,
    STATUS_PLANNED,
    ColdWorkflowError,
    ColdWorkflowService,
    ColdWorkflowSnapshot,
    _action_time,
    _audit,
    _remove_pending_cold_notifications,
    _snapshot,
)
from climatetest_manager.ui.formatters import format_datetime
from climatetest_manager.ui.theme import AppColors


def _configure_flow(
    self: ColdWorkflowService,
    test_id: int,
    *,
    cold_planned: bool,
    minimum_temperature: str = "",
) -> ColdWorkflowSnapshot:
    minimum = parse_minimum_ambient_service_temperature(minimum_temperature)
    with self._session_factory() as session:
        test = session.get(ClimateTestRecord, test_id)
        if test is None:
            raise ColdWorkflowError(f"Ensaio #{test_id} não encontrado.")
        if test.situation in {TestSituation.FINISHED.value, TestSituation.CANCELLED.value}:
            raise ColdWorkflowError(
                "O fluxo pós-calor não pode ser ativado retroativamente em ensaio encerrado."
            )
        workflow = session.get(ThermalColdWorkflowRecord, test_id)
        if workflow is None:
            workflow = ThermalColdWorkflowRecord(
                climate_test_id=test_id,
                cold_planned=cold_planned,
                minimum_ambient_service_temperature_c=(minimum if cold_planned else None),
                status=STATUS_PLANNED,
            )
            session.add(workflow)
        else:
            execution_started = bool(
                workflow.conditioning_started_at is not None or workflow.cold_started_at is not None
            )
            if execution_started and workflow.cold_planned != cold_planned:
                raise ColdWorkflowError(
                    "Depois do início do acondicionamento, altere a decisão sobre o frio "
                    "pela ação operacional 'Não realizar frio'."
                )
            if not execution_started:
                workflow.cold_planned = cold_planned
                workflow.minimum_ambient_service_temperature_c = minimum if cold_planned else None
                workflow.status = STATUS_PLANNED
        _audit(
            test,
            self._actor(),
            "Fluxo pós-calor configurado",
            (
                f"Acondicionamento: sim; frio: {'sim' if cold_planned else 'não'}; "
                f"Temperatura mínima ambiente de serviço: {minimum} °C"
                if cold_planned
                else "Acondicionamento: sim; frio: não"
            ),
            "Planejamento do ensaio",
        )
        session.commit()
        session.refresh(workflow)
        return _snapshot(workflow)


def _complete_heat(
    self: ColdWorkflowService,
    test_id: int,
    ended_at: datetime | None = None,
) -> None:
    now = self._now_provider().replace(microsecond=0)
    effective_end = _action_time(ended_at, now)
    with self._session_factory() as session:
        test = session.scalar(select(ClimateTestRecord).where(ClimateTestRecord.id == test_id))
        workflow = session.get(ThermalColdWorkflowRecord, test_id)
        if test is None or workflow is None:
            raise ColdWorkflowError("Este ensaio não possui fluxo pós-calor habilitado.")
        snapshot = test.condition_snapshot
        if test.situation == TestSituation.IN_CHAMBER.value:
            if snapshot is not None and snapshot.drying_required:
                raise ColdWorkflowError("Inicie a secagem antes de finalizar o ensaio de calor.")
            nominal = test.chamber_nominal_end_at
            test.chamber_ended_at = effective_end
        elif test.situation == TestSituation.DRYING.value:
            nominal = test.drying_nominal_end_at
            test.drying_ended_at = effective_end
        else:
            raise ColdWorkflowError("O ensaio não possui uma etapa de calor ativa para finalizar.")
        if nominal is not None and effective_end < nominal:
            raise ColdWorkflowError(
                "O ensaio de calor não pode ser finalizado antes do término nominal da etapa."
            )
        test.finished_at = None
        test.situation = TestSituation.AWAITING_CONDITIONING.value
        workflow.status = STATUS_AWAITING_CONDITIONING
        test.notifications[:] = [item for item in test.notifications if item.sent_at is not None]
        _audit(
            test,
            self._actor(),
            "Resistência térmica ao calor finalizada",
            f"Saída: {effective_end.isoformat(sep=' ', timespec='minutes')}",
            "Aguardando início do acondicionamento pós-calor",
        )
        session.commit()


def _start_conditioning(
    self: ColdWorkflowService,
    test_id: int,
    started_at: datetime | None = None,
) -> ColdWorkflowSnapshot:
    now = self._now_provider().replace(microsecond=0)
    effective_start = _action_time(started_at, now)
    window = conditioning_window(effective_start)
    with self._session_factory() as session:
        test = session.get(ClimateTestRecord, test_id)
        workflow = session.get(ThermalColdWorkflowRecord, test_id)
        if test is None or workflow is None:
            raise ColdWorkflowError("Este ensaio não possui fluxo pós-calor habilitado.")
        if test.situation != TestSituation.AWAITING_CONDITIONING.value:
            raise ColdWorkflowError("O ensaio ainda não está aguardando acondicionamento.")
        heat_ended = test.drying_ended_at or test.chamber_ended_at
        if heat_ended is not None and effective_start < heat_ended:
            raise ColdWorkflowError(
                "O acondicionamento não pode começar antes da saída da última etapa do calor."
            )
        workflow.conditioning_started_at = window.started_at
        workflow.conditioning_nominal_end_at = window.nominal_end_at
        workflow.conditioning_maximum_end_at = window.maximum_end_at
        workflow.conditioning_ended_at = None
        workflow.status = STATUS_CONDITIONING
        test.situation = TestSituation.CONDITIONING.value
        _audit(
            test,
            self._actor(),
            "Acondicionamento pós-calor iniciado",
            (
                f"Início: {window.started_at.isoformat(sep=' ', timespec='minutes')}; "
                f"mínimo: {window.nominal_end_at.isoformat(sep=' ', timespec='minutes')}; "
                f"limite: {window.maximum_end_at.isoformat(sep=' ', timespec='minutes')}"
            ),
            "Início operacional",
        )
        session.commit()
        session.refresh(workflow)
        return _snapshot(workflow)


def _finish_conditioning(
    self: ColdWorkflowService,
    test_id: int,
    ended_at: datetime | None = None,
) -> ColdWorkflowSnapshot:
    now = self._now_provider().replace(microsecond=0)
    effective_end = _action_time(ended_at, now)
    with self._session_factory() as session:
        test = session.get(ClimateTestRecord, test_id)
        workflow = session.get(ThermalColdWorkflowRecord, test_id)
        if test is None or workflow is None:
            raise ColdWorkflowError("Este ensaio não possui fluxo pós-calor habilitado.")
        if workflow.cold_planned:
            raise ColdWorkflowError(
                "Este ensaio possui frio planejado. Inicie a resistência térmica ao frio."
            )
        if test.situation != TestSituation.CONDITIONING.value:
            raise ColdWorkflowError("O ensaio não está em acondicionamento.")
        if workflow.conditioning_nominal_end_at is None:
            raise ColdWorkflowError("O prazo mínimo do acondicionamento não foi calculado.")
        if effective_end < workflow.conditioning_nominal_end_at:
            raise ColdWorkflowError(
                "O acondicionamento não pode ser finalizado antes de completar 24 horas."
            )
        late = bool(
            workflow.conditioning_maximum_end_at
            and effective_end > workflow.conditioning_maximum_end_at
        )
        workflow.conditioning_ended_at = effective_end
        workflow.status = STATUS_COMPLETED_LATE if late else STATUS_COMPLETED
        test.finished_at = effective_end
        test.situation = TestSituation.FINISHED.value
        _remove_pending_cold_notifications(test)
        _audit(
            test,
            self._actor(),
            "Acondicionamento pós-calor finalizado",
            f"Fim: {effective_end.isoformat(sep=' ', timespec='minutes')}",
            "Finalizado após o limite de 72 h" if late else "Conclusão operacional",
        )
        session.commit()
        session.refresh(workflow)
        return _snapshot(workflow)


def _finish_with_conditioning(
    self: ClimateTestService,
    test_id: int,
    finished_at: datetime | None = None,
) -> None:
    workflow = v086_runtime._service_for_climate(self).get(test_id)
    if workflow is not None and workflow.conditioning_started_at is None:
        v086_runtime._service_for_climate(self).complete_heat(test_id, finished_at)
        return
    v086_runtime._ORIGINAL_FINISH(self, test_id, finished_at)


def _save_test_with_conditioning(app, command, planned: bool, minimum_temperature: str) -> None:
    if planned:
        parse_minimum_ambient_service_temperature(minimum_temperature)
    test_id = app._service.create(command)
    cold = v086_runtime._service_for_app(app)
    cold.configure_flow(
        test_id,
        cold_planned=planned,
        minimum_temperature=minimum_temperature,
    )
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


def _update_test_with_conditioning(
    app,
    test_id: int,
    command,
    planned: bool,
    minimum_temperature: str,
) -> None:
    try:
        if planned:
            parse_minimum_ambient_service_temperature(minimum_temperature)
        app._service.update(test_id, command)
        cold = v086_runtime._service_for_app(app)
        existing = cold.get(test_id)
        if existing is not None or planned:
            cold.configure_flow(
                test_id,
                cold_planned=planned,
                minimum_temperature=minimum_temperature,
            )
    except (ValueError, LookupError) as error:
        app._show_message(str(error), error=True)
        return
    app.show_details(test_id)
    app._show_message("Dados corrigidos e alteração registrada.")


def _conditioning_only_phase_panel(self):
    original = _ORIGINAL_PHASE_PANEL(self)
    workflow = self._v086_cold
    if workflow is None or workflow.cold_planned:
        return original
    conditioning = v086_runtime._phase_card(
        "Acondicionamento pós-calor",
        ft.Icons.HOURGLASS_BOTTOM,
        [
            "20 ± 5 °C • 50 ± 10 % UR • 24 a 72 h",
            f"Início: {format_datetime(workflow.conditioning_started_at)}",
            f"Mínimo: {format_datetime(workflow.conditioning_nominal_end_at)}",
            f"Limite: {format_datetime(workflow.conditioning_maximum_end_at)}",
        ],
        emphasis=self._details.situation == TestSituation.CONDITIONING.value,
    )
    try:
        responsive = original.content.controls[1]
        responsive.controls.append(ft.Container(col={"xs": 12, "md": 6}, content=conditioning))
        return original
    except (AttributeError, IndexError, TypeError):
        return ft.Column(spacing=9, controls=[original, conditioning])


def _conditioning_only_action_panel(self):
    base = _ORIGINAL_ACTION_PANEL(self)
    workflow = self._v086_cold
    if workflow is None or workflow.cold_planned or not self._r7_can_operate:
        return base
    situation = self._details.situation
    if situation == TestSituation.AWAITING_CONDITIONING.value:
        action = ft.Container(
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
                    ft.Button(
                        content="Iniciar acondicionamento",
                        icon=ft.Icons.HOURGLASS_BOTTOM,
                        bgcolor=AppColors.PRIMARY,
                        color=AppColors.WHITE,
                        on_click=lambda _event: self._time_dialog(
                            "Iniciar acondicionamento",
                            self._v086_start_conditioning,
                        ),
                    ),
                ],
            ),
        )
        return ft.Column(spacing=9, controls=[base, action])
    if situation != TestSituation.CONDITIONING.value:
        return base
    ready = bool(
        workflow.conditioning_nominal_end_at
        and datetime.now().replace(microsecond=0) >= workflow.conditioning_nominal_end_at
    )
    action = ft.Container(
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
                ft.Button(
                    content="Finalizar acondicionamento",
                    icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                    disabled=not ready,
                    tooltip=(
                        None if ready else "Disponível após completar 24 h de acondicionamento."
                    ),
                    bgcolor=AppColors.PRIMARY if ready else None,
                    color=AppColors.WHITE if ready else None,
                    on_click=(
                        lambda _event: (
                            self._time_dialog(
                                "Finalizar acondicionamento",
                                self._v086_finish_cold,
                            )
                            if ready
                            else None
                        )
                    ),
                ),
            ],
        ),
    )
    return ft.Column(spacing=9, controls=[base, action])


def _show_details(self: production_app.ProductionClimateTestApplication, test_id: int) -> None:
    self._prepare_theme()
    self._active_test_id = test_id
    details = self._service.get_details(test_id)
    cold_service = v086_runtime._service_for_app(self)
    workflow = cold_service.get(test_id)

    def finish_cold_or_conditioning(value: datetime | None) -> None:
        current = cold_service.get(test_id)
        if current is not None and not current.cold_planned:
            v086_runtime._cold_perform(
                self,
                test_id,
                lambda: cold_service.finish_conditioning(test_id, value),
                "Acondicionamento finalizado e ensaio concluído.",
            )
            return
        v086_runtime._cold_perform(
            self,
            test_id,
            lambda: cold_service.finish_cold(test_id, value),
            "Retirada do frio registrada e ensaio finalizado.",
        )

    view = v086_runtime.V086DetailsView(
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
                if workflow is not None
                else "Ensaio finalizado."
            ),
        ),
        on_start_conditioning=lambda value: v086_runtime._cold_perform(
            self,
            test_id,
            lambda: cold_service.start_conditioning(test_id, value),
            "Acondicionamento iniciado e janela de 24 a 72 h calculada.",
        ),
        on_start_cold=lambda value: v086_runtime._cold_perform(
            self,
            test_id,
            lambda: cold_service.start_cold(test_id, value),
            "Ensaio de frio iniciado. Alertas de retirada foram agendados.",
        ),
        on_finish_cold=finish_cold_or_conditioning,
        on_skip_cold=lambda reason: v086_runtime._cold_perform(
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


_ORIGINAL_PHASE_PANEL = v086_runtime.V086DetailsView._phase_panel
_ORIGINAL_ACTION_PANEL = v086_runtime.V086DetailsView._action_panel


def install() -> None:
    if getattr(production_app, "_v086_conditioning_installed", False):
        return
    ColdWorkflowService.configure_flow = _configure_flow
    ColdWorkflowService.complete_heat = _complete_heat
    ColdWorkflowService.start_conditioning = _start_conditioning
    ColdWorkflowService.finish_conditioning = _finish_conditioning
    ClimateTestService.finish = _finish_with_conditioning
    v086_runtime._save_test_with_cold = _save_test_with_conditioning
    v086_runtime._update_test_with_cold = _update_test_with_conditioning
    v086_runtime.V086DetailsView._phase_panel = _conditioning_only_phase_panel
    v086_runtime.V086DetailsView._action_panel = _conditioning_only_action_panel
    production_app.ProductionClimateTestApplication.show_details = _show_details
    production_app._v086_conditioning_installed = True
