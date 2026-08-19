"""Estado visual correto das novas etapas na tela de detalhes."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from climatetest_manager import v086_runtime
from climatetest_manager.domain.enums import TestSituation
from climatetest_manager.services.climate_tests import ClimateTestService
from climatetest_manager.services.scheduling import classify_deadline

_ORIGINAL_GET_DETAILS = ClimateTestService.get_details


def _progress(
    now: datetime,
    started_at: datetime | None,
    nominal_end_at: datetime | None,
) -> float:
    if started_at is None or nominal_end_at is None or nominal_end_at <= started_at:
        return 0.0
    elapsed = max((now - started_at).total_seconds(), 0.0)
    duration = (nominal_end_at - started_at).total_seconds()
    return min(elapsed / duration, 1.0)


def _get_details_with_post_heat_state(self: ClimateTestService, test_id: int):
    details = _ORIGINAL_GET_DETAILS(self, test_id)
    workflow = v086_runtime._service_for_climate(self).get(test_id)
    if workflow is None:
        return details

    now = self._now_provider().replace(microsecond=0)
    if details.situation == TestSituation.AWAITING_CONDITIONING.value:
        return replace(
            details,
            deadline_condition=None,
            progress_percent=0.0,
            progress_label="Aguardando início do acondicionamento pós-calor",
        )

    if details.situation == TestSituation.CONDITIONING.value:
        nominal = workflow.conditioning_nominal_end_at
        maximum = workflow.conditioning_maximum_end_at
        deadline = (
            classify_deadline(now, nominal, maximum).value
            if nominal is not None and maximum is not None
            else None
        )
        if nominal is None:
            label = "Aguardando cálculo do prazo"
        elif now < nominal:
            label = "Acondicionamento em andamento"
        elif maximum is not None and now <= maximum:
            label = "Mínimo de 24 h concluído • próxima etapa disponível"
        else:
            label = "Limite de 72 h ultrapassado"
        return replace(
            details,
            deadline_condition=deadline,
            progress_percent=_progress(now, workflow.conditioning_started_at, nominal),
            progress_label=label,
        )

    if details.situation == TestSituation.IN_COLD.value:
        nominal = workflow.cold_nominal_end_at
        maximum = workflow.cold_maximum_end_at
        deadline = (
            classify_deadline(now, nominal, maximum).value
            if nominal is not None and maximum is not None
            else None
        )
        if nominal is None:
            label = "Aguardando cálculo do prazo"
        elif now < nominal:
            label = "Resistência térmica ao frio em andamento"
        elif maximum is not None and now <= maximum:
            label = "24 h concluídas • retirar até o limite de 26 h"
        else:
            label = "Limite de 26 h ultrapassado"
        return replace(
            details,
            deadline_condition=deadline,
            progress_percent=_progress(now, workflow.cold_started_at, nominal),
            progress_label=label,
        )

    return details


def install() -> None:
    ClimateTestService.get_details = _get_details_with_post_heat_state
