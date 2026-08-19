"""Casos de uso do fluxo opcional pós-calor da v0.8.6.

A implementação fica isolada do fluxo legado: somente ensaios explicitamente
planejados recebem um registro em ``thermal_cold_workflows``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from climatetest_manager.database.cold_models import ThermalColdWorkflowRecord
from climatetest_manager.database.models import AuditEvent, ClimateTestRecord, NotificationEvent
from climatetest_manager.domain.cold_flow import (
    ColdTemperatureRange,
    cold_temperature_range,
    cold_window,
    conditioning_window,
    parse_minimum_ambient_service_temperature,
)
from climatetest_manager.domain.enums import TestSituation

STATUS_PLANNED = "planned"
STATUS_AWAITING_CONDITIONING = "awaiting_conditioning"
STATUS_CONDITIONING = "conditioning"
STATUS_COLD = "cold"
STATUS_COMPLETED = "completed"
STATUS_COMPLETED_LATE = "completed_late"
STATUS_SKIPPED = "skipped"


class ColdWorkflowError(ValueError):
    """Indica uma transição inválida do fluxo pós-calor."""


@dataclass(frozen=True, slots=True)
class ColdWorkflowSnapshot:
    climate_test_id: int
    cold_planned: bool
    minimum_ambient_service_temperature_c: Decimal
    temperature_range: ColdTemperatureRange
    conditioning_started_at: datetime | None
    conditioning_nominal_end_at: datetime | None
    conditioning_maximum_end_at: datetime | None
    conditioning_ended_at: datetime | None
    cold_started_at: datetime | None
    cold_nominal_end_at: datetime | None
    cold_maximum_end_at: datetime | None
    cold_ended_at: datetime | None
    cold_skipped_at: datetime | None
    cold_skip_reason: str | None
    status: str


def _snapshot(record: ThermalColdWorkflowRecord) -> ColdWorkflowSnapshot:
    minimum = (
        record.minimum_ambient_service_temperature_c
        if record.minimum_ambient_service_temperature_c is not None
        else parse_minimum_ambient_service_temperature("")
    )
    return ColdWorkflowSnapshot(
        climate_test_id=record.climate_test_id,
        cold_planned=record.cold_planned,
        minimum_ambient_service_temperature_c=minimum,
        temperature_range=cold_temperature_range(minimum),
        conditioning_started_at=record.conditioning_started_at,
        conditioning_nominal_end_at=record.conditioning_nominal_end_at,
        conditioning_maximum_end_at=record.conditioning_maximum_end_at,
        conditioning_ended_at=record.conditioning_ended_at,
        cold_started_at=record.cold_started_at,
        cold_nominal_end_at=record.cold_nominal_end_at,
        cold_maximum_end_at=record.cold_maximum_end_at,
        cold_ended_at=record.cold_ended_at,
        cold_skipped_at=record.cold_skipped_at,
        cold_skip_reason=record.cold_skip_reason,
        status=record.status,
    )


def _action_time(value: datetime | None, now: datetime) -> datetime:
    resolved = (value or now).replace(microsecond=0)
    if resolved > now + timedelta(minutes=1):
        raise ColdWorkflowError("A data e hora não podem estar no futuro.")
    return resolved


def _audit(record: ClimateTestRecord, actor: str, action: str, value: str, reason: str) -> None:
    record.audit_events.append(
        AuditEvent(
            actor=actor.strip() or "Não identificado",
            action=action,
            new_value=value,
            reason=reason,
        )
    )


def _remove_pending_cold_notifications(record: ClimateTestRecord) -> None:
    record.notifications[:] = [
        item
        for item in record.notifications
        if item.sent_at is not None or not item.event_key.startswith("cold-")
    ]


def _schedule_cold_notifications(
    record: ClimateTestRecord,
    *,
    nominal_end_at: datetime,
    maximum_end_at: datetime,
) -> None:
    """Agenda somente os alertas pedidos para a etapa de frio.

    O mesmo ``NotificationEvent`` alimenta aviso interno/desktop e e-mail pelo
    agente já existente. Não há notificação de início do ensaio de calor.
    """

    definitions = (
        (
            "cold-one-hour",
            "Retirada do frio em 1 hora",
            (
                f"Cliente: {record.client} | Produto: {record.product} | "
                f"Processo: {record.process_number}. A retirada nominal do ensaio "
                "de resistência térmica ao frio ocorrerá em 1 hora."
            ),
            nominal_end_at - timedelta(hours=1),
        ),
        (
            "cold-near-limit",
            "Atenção ao limite do ensaio de frio",
            (
                f"Cliente: {record.client} | Produto: {record.product} | "
                f"Processo: {record.process_number}. Restam 30 minutos para o limite "
                "máximo de permanência no frio."
            ),
            maximum_end_at - timedelta(minutes=30),
        ),
        (
            "cold-maximum",
            "Limite do ensaio de frio atingido",
            (
                f"Cliente: {record.client} | Produto: {record.product} | "
                f"Processo: {record.process_number}. O limite máximo de 26 horas do "
                "ensaio de resistência térmica ao frio foi atingido."
            ),
            maximum_end_at,
        ),
    )
    _remove_pending_cold_notifications(record)
    for key, title, message, scheduled_for in definitions:
        record.notifications.append(
            NotificationEvent(
                event_key=key,
                title=title,
                message=message,
                scheduled_for_at=scheduled_for,
            )
        )


class ColdWorkflowService:
    """Persiste e valida o fluxo opcional calor -> acondicionamento -> frio."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        now_provider: Callable[[], datetime] = datetime.now,
        actor_provider: Callable[[], str] = lambda: "Não identificado",
    ) -> None:
        self._session_factory = session_factory
        self._now_provider = now_provider
        self._actor_provider = actor_provider

    def _actor(self) -> str:
        return self._actor_provider().strip() or "Não identificado"

    def get(self, test_id: int) -> ColdWorkflowSnapshot | None:
        with self._session_factory() as session:
            record = session.get(ThermalColdWorkflowRecord, test_id)
            return _snapshot(record) if record is not None else None

    def plan(self, test_id: int, minimum_temperature: str = "") -> ColdWorkflowSnapshot:
        minimum = parse_minimum_ambient_service_temperature(minimum_temperature)
        with self._session_factory() as session:
            test = session.get(ClimateTestRecord, test_id)
            if test is None:
                raise ColdWorkflowError(f"Ensaio #{test_id} não encontrado.")
            if test.situation in {TestSituation.FINISHED.value, TestSituation.CANCELLED.value}:
                raise ColdWorkflowError(
                    "O ensaio já está encerrado; o fluxo de frio não pode ser ativado retroativamente."
                )
            workflow = session.get(ThermalColdWorkflowRecord, test_id)
            if workflow is None:
                workflow = ThermalColdWorkflowRecord(
                    climate_test_id=test_id,
                    cold_planned=True,
                    minimum_ambient_service_temperature_c=minimum,
                    status=STATUS_PLANNED,
                )
                session.add(workflow)
            else:
                if (
                    workflow.conditioning_started_at is not None
                    or workflow.cold_started_at is not None
                ):
                    raise ColdWorkflowError(
                        "A temperatura planejada não pode ser substituída depois do início "
                        "do acondicionamento/frio sem tratamento técnico específico."
                    )
                workflow.cold_planned = True
                workflow.minimum_ambient_service_temperature_c = minimum
                workflow.status = STATUS_PLANNED
            _audit(
                test,
                self._actor(),
                "Resistência térmica ao frio planejada",
                f"Temperatura mínima ambiente de serviço: {minimum} °C",
                "Planejamento do ensaio",
            )
            session.commit()
            session.refresh(workflow)
            return _snapshot(workflow)

    def remove_plan(self, test_id: int, *, reason: str = "Frio não previsto") -> None:
        with self._session_factory() as session:
            test = session.get(ClimateTestRecord, test_id)
            workflow = session.get(ThermalColdWorkflowRecord, test_id)
            if test is None:
                raise ColdWorkflowError(f"Ensaio #{test_id} não encontrado.")
            if workflow is None:
                return
            if workflow.conditioning_started_at is not None or workflow.cold_started_at is not None:
                raise ColdWorkflowError(
                    "O fluxo já possui execução registrada. Use 'Não realizar frio' com justificativa."
                )
            session.delete(workflow)
            _audit(
                test,
                self._actor(),
                "Planejamento do frio removido",
                "Fluxo pós-calor desativado",
                reason,
            )
            session.commit()

    def complete_heat(self, test_id: int, ended_at: datetime | None = None) -> None:
        """Encerra a última etapa do calor sem finalizar o ensaio que terá frio."""

        now = self._now_provider().replace(microsecond=0)
        effective_end = _action_time(ended_at, now)
        with self._session_factory() as session:
            test = session.scalar(select(ClimateTestRecord).where(ClimateTestRecord.id == test_id))
            workflow = session.get(ThermalColdWorkflowRecord, test_id)
            if test is None or workflow is None or not workflow.cold_planned:
                raise ColdWorkflowError(
                    "Este ensaio não possui resistência térmica ao frio planejada."
                )
            snapshot = test.condition_snapshot
            if test.situation == TestSituation.IN_CHAMBER.value:
                if snapshot is not None and snapshot.drying_required:
                    raise ColdWorkflowError(
                        "Inicie a secagem antes de finalizar o ensaio de calor."
                    )
                nominal = test.chamber_nominal_end_at
                test.chamber_ended_at = effective_end
            elif test.situation == TestSituation.DRYING.value:
                nominal = test.drying_nominal_end_at
                test.drying_ended_at = effective_end
            else:
                raise ColdWorkflowError(
                    "O ensaio não possui uma etapa de calor ativa para finalizar."
                )
            if nominal is not None and effective_end < nominal:
                raise ColdWorkflowError(
                    "O ensaio de calor não pode ser finalizado antes do término nominal da etapa."
                )
            test.finished_at = None
            test.situation = TestSituation.AWAITING_CONDITIONING.value
            workflow.status = STATUS_AWAITING_CONDITIONING
            test.notifications[:] = [
                item for item in test.notifications if item.sent_at is not None
            ]
            _audit(
                test,
                self._actor(),
                "Resistência térmica ao calor finalizada",
                f"Saída: {effective_end.isoformat(sep=' ', timespec='minutes')}",
                "Aguardando início do acondicionamento pós-calor",
            )
            session.commit()

    def start_conditioning(
        self,
        test_id: int,
        started_at: datetime | None = None,
    ) -> ColdWorkflowSnapshot:
        now = self._now_provider().replace(microsecond=0)
        effective_start = _action_time(started_at, now)
        window = conditioning_window(effective_start)
        with self._session_factory() as session:
            test = session.get(ClimateTestRecord, test_id)
            workflow = session.get(ThermalColdWorkflowRecord, test_id)
            if test is None or workflow is None or not workflow.cold_planned:
                raise ColdWorkflowError("Este ensaio não possui fluxo de frio planejado.")
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

    def start_cold(
        self,
        test_id: int,
        started_at: datetime | None = None,
    ) -> ColdWorkflowSnapshot:
        now = self._now_provider().replace(microsecond=0)
        effective_start = _action_time(started_at, now)
        window = cold_window(effective_start)
        with self._session_factory() as session:
            test = session.get(ClimateTestRecord, test_id)
            workflow = session.get(ThermalColdWorkflowRecord, test_id)
            if test is None or workflow is None or not workflow.cold_planned:
                raise ColdWorkflowError("Este ensaio não possui fluxo de frio planejado.")
            if test.situation != TestSituation.CONDITIONING.value:
                raise ColdWorkflowError("O ensaio não está em acondicionamento.")
            if workflow.conditioning_nominal_end_at is None:
                raise ColdWorkflowError("O prazo mínimo do acondicionamento não foi calculado.")
            if effective_start < workflow.conditioning_nominal_end_at:
                raise ColdWorkflowError(
                    "O frio não pode iniciar antes de completar 24 horas de acondicionamento."
                )
            workflow.conditioning_ended_at = effective_start
            workflow.cold_started_at = window.started_at
            workflow.cold_nominal_end_at = window.nominal_end_at
            workflow.cold_maximum_end_at = window.maximum_end_at
            workflow.cold_ended_at = None
            workflow.status = STATUS_COLD
            test.situation = TestSituation.IN_COLD.value
            _schedule_cold_notifications(
                test,
                nominal_end_at=window.nominal_end_at,
                maximum_end_at=window.maximum_end_at,
            )
            late_conditioning = bool(
                workflow.conditioning_maximum_end_at
                and effective_start > workflow.conditioning_maximum_end_at
            )
            _audit(
                test,
                self._actor(),
                "Resistência térmica ao frio iniciada",
                (
                    f"Entrada: {window.started_at.isoformat(sep=' ', timespec='minutes')}; "
                    f"retirada nominal: {window.nominal_end_at.isoformat(sep=' ', timespec='minutes')}; "
                    f"limite: {window.maximum_end_at.isoformat(sep=' ', timespec='minutes')}"
                ),
                (
                    "Início após o limite de 72 h do acondicionamento"
                    if late_conditioning
                    else "Início operacional"
                ),
            )
            session.commit()
            session.refresh(workflow)
            return _snapshot(workflow)

    def finish_cold(
        self,
        test_id: int,
        ended_at: datetime | None = None,
    ) -> ColdWorkflowSnapshot:
        now = self._now_provider().replace(microsecond=0)
        effective_end = _action_time(ended_at, now)
        with self._session_factory() as session:
            test = session.get(ClimateTestRecord, test_id)
            workflow = session.get(ThermalColdWorkflowRecord, test_id)
            if test is None or workflow is None or test.situation != TestSituation.IN_COLD.value:
                raise ColdWorkflowError(
                    "O ensaio não está na etapa de resistência térmica ao frio."
                )
            if workflow.cold_nominal_end_at is None or workflow.cold_maximum_end_at is None:
                raise ColdWorkflowError("Os prazos do ensaio de frio não foram calculados.")
            if effective_end < workflow.cold_nominal_end_at:
                raise ColdWorkflowError(
                    "A retirada não pode ser registrada antes de completar 24 horas no frio."
                )
            late = effective_end > workflow.cold_maximum_end_at
            workflow.cold_ended_at = effective_end
            workflow.status = STATUS_COMPLETED_LATE if late else STATUS_COMPLETED
            test.finished_at = effective_end
            test.situation = TestSituation.FINISHED.value
            _remove_pending_cold_notifications(test)
            _audit(
                test,
                self._actor(),
                "Resistência térmica ao frio finalizada",
                f"Retirada: {effective_end.isoformat(sep=' ', timespec='minutes')}",
                "Retirada após o limite de 26 h" if late else "Conclusão operacional",
            )
            session.commit()
            session.refresh(workflow)
            return _snapshot(workflow)

    def skip_cold(self, test_id: int, reason: str) -> ColdWorkflowSnapshot:
        normalized_reason = reason.strip()
        if len(normalized_reason) < 8:
            raise ColdWorkflowError("Informe uma justificativa com pelo menos 8 caracteres.")
        now = self._now_provider().replace(microsecond=0)
        with self._session_factory() as session:
            test = session.get(ClimateTestRecord, test_id)
            workflow = session.get(ThermalColdWorkflowRecord, test_id)
            if test is None or workflow is None or not workflow.cold_planned:
                raise ColdWorkflowError("Este ensaio não possui frio planejado.")
            if workflow.cold_started_at is not None:
                raise ColdWorkflowError(
                    "O frio já foi iniciado. Registre a retirada em vez de marcar como não realizado."
                )
            if test.situation not in {
                TestSituation.AWAITING_CONDITIONING.value,
                TestSituation.CONDITIONING.value,
            }:
                raise ColdWorkflowError(
                    "O frio só pode ser marcado como não realizado após o encerramento do calor."
                )
            workflow.cold_skipped_at = now
            workflow.cold_skip_reason = normalized_reason
            workflow.status = STATUS_SKIPPED
            test.finished_at = now
            test.situation = TestSituation.FINISHED.value
            _remove_pending_cold_notifications(test)
            _audit(
                test,
                self._actor(),
                "Resistência térmica ao frio não realizada",
                "Etapa de frio encerrada sem execução",
                normalized_reason,
            )
            session.commit()
            session.refresh(workflow)
            return _snapshot(workflow)
