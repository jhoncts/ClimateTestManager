"""Acompanhamento das novas etapas no Dashboard e na Agenda da v0.8.6."""

from __future__ import annotations

from datetime import datetime

from climatetest_manager.domain.enums import DeadlineCondition, TestSituation
from climatetest_manager.services.climate_tests import AgendaEvent, ClimateTestService


def _list_dashboard_tests(self: ClimateTestService):
    active_situations = {
        TestSituation.WAITING.value,
        TestSituation.IN_CHAMBER.value,
        TestSituation.DRYING.value,
        TestSituation.AWAITING_CONDITIONING.value,
        TestSituation.CONDITIONING.value,
        TestSituation.IN_COLD.value,
    }
    priority = {
        DeadlineCondition.OVERDUE.value: 0,
        DeadlineCondition.DUE_TODAY.value: 1,
        DeadlineCondition.IN_TOLERANCE.value: 2,
        DeadlineCondition.ON_TIME.value: 3,
        None: 4,
    }
    items = [item for item in self.list_tests() if item.situation in active_situations]
    return sorted(
        items,
        key=lambda item: (
            0 if item.is_paused else 1,
            priority[item.deadline_condition],
            item.nominal_end_at or datetime.max,
            item.id,
        ),
    )


def _agenda_labels(situation: str) -> tuple[str, str, str] | None:
    if situation == TestSituation.IN_CHAMBER.value:
        return "Câmara climática", "Retirar a partir de", "Limite para retirada"
    if situation == TestSituation.DRYING.value:
        return "Secagem", "Retirar a partir de", "Limite para retirada"
    if situation == TestSituation.CONDITIONING.value:
        return (
            "Acondicionamento pós-calor",
            "Mínimo de 24 h concluído",
            "Limite de 72 h",
        )
    if situation == TestSituation.IN_COLD.value:
        return (
            "Resistência térmica ao frio",
            "Retirada nominal — 24 h",
            "Limite para retirada — 26 h",
        )
    return None


def _list_agenda_events(self: ClimateTestService) -> list[AgendaEvent]:
    events: list[AgendaEvent] = []
    for item in self.list_dashboard_tests():
        labels = _agenda_labels(item.situation)
        if labels is None:
            continue
        phase, nominal_label, maximum_label = labels
        if item.nominal_end_at is not None:
            events.append(
                AgendaEvent(
                    test_id=item.id,
                    process_number=item.process_number,
                    client=item.client,
                    phase=phase,
                    kind=nominal_label,
                    occurs_at=item.nominal_end_at,
                    is_paused=item.is_paused,
                )
            )
        if item.maximum_end_at is not None:
            events.append(
                AgendaEvent(
                    test_id=item.id,
                    process_number=item.process_number,
                    client=item.client,
                    phase=phase,
                    kind=maximum_label,
                    occurs_at=item.maximum_end_at,
                    is_paused=item.is_paused,
                )
            )
    return sorted(events, key=lambda item: (item.occurs_at, item.test_id, item.kind))


def install() -> None:
    ClimateTestService.list_dashboard_tests = _list_dashboard_tests
    ClimateTestService.list_agenda_events = _list_agenda_events
