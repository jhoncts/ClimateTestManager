from datetime import datetime, timedelta
from decimal import Decimal

from climatetest_manager.database.models import ClimateConditionSnapshot, ClimateTestRecord
from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.domain.enums import TestSituation
from climatetest_manager.services.cold_workflows import ColdWorkflowService
from climatetest_manager.v086_conditioning import (
    _complete_heat,
    _configure_flow,
    _finish_conditioning,
    _start_conditioning,
)


class Clock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


def _create_heat_test(session_factory) -> int:
    record = ClimateTestRecord(
        client="Cliente",
        process_number="26002.1",
        product="Produto sem frio",
        ex_marking="",
        epl="Gb",
        tamb_max_c=Decimal("40"),
        delta_t_max_k=Decimal("35"),
        service_temperature_c=Decimal("75"),
        selected_option="A",
        situation=TestSituation.IN_CHAMBER.value,
        chamber_started_at=datetime(2026, 8, 1, 8, 0),
        chamber_nominal_end_at=datetime(2026, 8, 19, 8, 0),
        chamber_maximum_end_at=datetime(2026, 8, 20, 14, 0),
        condition_snapshot=ClimateConditionSnapshot(
            rule_id="TEST",
            normative_rule_version="test",
            option="A",
            service_temperature_c=Decimal("75"),
            chamber_temperature_c=Decimal("90"),
            chamber_temperature_tolerance_k=Decimal("2"),
            chamber_humidity_percent=Decimal("90"),
            chamber_humidity_tolerance_percent=Decimal("5"),
            chamber_duration_hours=432,
            chamber_duration_positive_tolerance_hours=30,
            drying_required=False,
            drying_temperature_c=None,
            drying_temperature_tolerance_k=None,
            drying_duration_hours=None,
            drying_duration_positive_tolerance_hours=None,
        ),
    )
    with session_factory() as session:
        session.add(record)
        session.commit()
        return record.id


def test_new_test_without_cold_still_runs_post_heat_conditioning(tmp_path) -> None:
    engine = initialize_database(tmp_path / "conditioning.db")
    session_factory = create_session_factory(engine)
    clock = Clock(datetime(2026, 8, 19, 8, 0))
    service = ColdWorkflowService(
        session_factory,
        now_provider=clock.now,
        actor_provider=lambda: "Operador",
    )
    try:
        test_id = _create_heat_test(session_factory)
        configured = _configure_flow(
            service,
            test_id,
            cold_planned=False,
            minimum_temperature="",
        )
        assert configured.cold_planned is False

        _complete_heat(service, test_id, clock.value)
        with session_factory() as session:
            record = session.get(ClimateTestRecord, test_id)
            assert record is not None
            assert record.situation == TestSituation.AWAITING_CONDITIONING.value
            assert record.finished_at is None

        conditioning = _start_conditioning(service, test_id, clock.value)
        assert conditioning.conditioning_nominal_end_at == clock.value + timedelta(hours=24)
        assert conditioning.conditioning_maximum_end_at == clock.value + timedelta(hours=72)

        clock.value += timedelta(hours=24)
        finished = _finish_conditioning(service, test_id, clock.value)
        assert finished.conditioning_ended_at == clock.value
        with session_factory() as session:
            record = session.get(ClimateTestRecord, test_id)
            assert record is not None
            assert record.situation == TestSituation.FINISHED.value
            assert record.finished_at == clock.value
            assert not [item for item in record.notifications if item.event_key.startswith("cold-")]
    finally:
        engine.dispose()
