"""Política de desistência do frio sem pular o acondicionamento pós-calor."""

from __future__ import annotations

from climatetest_manager.database.cold_models import ThermalColdWorkflowRecord
from climatetest_manager.database.models import ClimateTestRecord
from climatetest_manager.domain.enums import TestSituation
from climatetest_manager.services.cold_workflows import (
    STATUS_AWAITING_CONDITIONING,
    STATUS_CONDITIONING,
    ColdWorkflowError,
    ColdWorkflowService,
    ColdWorkflowSnapshot,
    _audit,
    _remove_pending_cold_notifications,
    _snapshot,
)


def _skip_cold_keep_conditioning(
    self: ColdWorkflowService,
    test_id: int,
    reason: str,
) -> ColdWorkflowSnapshot:
    """Cancela somente o 26.9; o acondicionamento continua até sua conclusão."""

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

        workflow.cold_planned = False
        workflow.cold_skipped_at = now
        workflow.cold_skip_reason = normalized_reason
        workflow.status = (
            STATUS_CONDITIONING
            if test.situation == TestSituation.CONDITIONING.value
            else STATUS_AWAITING_CONDITIONING
        )
        _remove_pending_cold_notifications(test)
        _audit(
            test,
            self._actor(),
            "Resistência térmica ao frio não será realizada",
            "Etapa de frio removida; acondicionamento pós-calor mantido",
            normalized_reason,
        )
        session.commit()
        session.refresh(workflow)
        return _snapshot(workflow)


def install() -> None:
    ColdWorkflowService.skip_cold = _skip_cold_keep_conditioning
