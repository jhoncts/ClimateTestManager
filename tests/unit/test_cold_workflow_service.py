from datetime import datetime, timedelta
from decimal import Decimal

from climatetest_manager.database.models import ClimateConditionSnapshot, ClimateTestRecord
from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.domain.enums import TestSituation
from climatetest_manager.services.cold_workflows import ColdWorkflowService


class Clock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


def _create_test(session_factory) -> int:
    record = ClimateTestRecord(
        client="Cliente",
        process_number="26001.1",
        product="Produto",
        ex_marking="",
        epl="Gb",
        tamb_max_c=Decimal("40"),
        delta_t_max_k=Decimal("35"),
        service_temperature_c=Decimal("75"),
        selected_option="A",
        situation=TestSituation.IN_CHAMBER.value,
        chamber_started_at=datetime(2026, 8, 1, 8, 0),
        chamber_nominal_end_at=datetime(2026, 8, 18, 8, 0),
        chamber_maximum_end_at=datetime(2026, 8, 19, 14, 0),
        condition_snapshot=ClimateConditionSnapshot(
            rule_id="TEST",
            normative_rule_version="test",
            option="A",
            service_temperature_c=Decimal("75"),
            chamber_temperature_c=Decimal("90"),
            chamber_temperature_tolerance_k=Decimal("2"),
            chamber_humidity_percent=Decimal("90"),
            chamber_humidity_tolerance_percent=Decimal("5"),
            chamber_duration_hours=408,
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


def test_full_optional_cold_workflow_finishes_without_reinterpreting_heat(tmp_path) -> None:
    engine = initialize_database(tmp_path / "cold.db")
    session_factory = create_session_factory(engine)
    clock = Clock(datetime(2026, 8, 19, 8, 0))
    service = ColdWorkflowService(
        session_factory,
        now_provider=clock.now,
        actor_provider=lambda: "Operador",
    )
    try:
        test_id = _create_test(session_factory)

        planned = service.plan(test_id, "-20")
        assert planned.minimum_ambient_service_temperature_c == Decimal("-20")
        assert planned.temperature_range.minimum_c == Decimal("-30")
        assert planned.temperature_range.maximum_c == Decimal("-25")

        service.complete_heat(test_id, clock.value)
        with session_factory() as session:
            test = session.get(ClimateTestRecord, test_id)
            assert test is not None
            assert test.situation == TestSituation.AWAITING_CONDITIONING.value
            assert test.finished_at is None

        conditioning = service.start_conditioning(test_id, clock.value)
        assert conditioning.conditioning_nominal_end_at == clock.value + timedelta(hours=24)
        assert conditioning.conditioning_maximum_end_at == clock.value + timedelta(hours=72)

        clock.value += timedelta(hours=24)
        cold = service.start_cold(test_id, clock.value)
        assert cold.cold_nominal_end_at == clock.value + timedelta(hours=24)
        assert cold.cold_maximum_end_at == clock.value + timedelta(hours=26)
        with session_factory() as session:
            test = session.get(ClimateTestRecord, test_id)
            assert test is not None
            pending = [item for item in test.notifications if item.sent_at is None]
            assert {item.event_key for item in pending} == {
                "cold-one-hour",
                "cold-near-limit",
                "cold-maximum",
            }

        clock.value += timedelta(hours=24)
        finished = service.finish_cold(test_id, clock.value)
        assert finished.cold_ended_at == clock.value
        with session_factory() as session:
            test = session.get(ClimateTestRecord, test_id)
            assert test is not None
            assert test.situation == TestSituation.FINISHED.value
            assert test.finished_at == clock.value
            assert not [item for item in test.notifications if item.sent_at is None]
    finally:
        engine.dispose()
