"""Testes do caso de uso de cadastro de ensaio."""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import select

from climatetest_manager.database.models import ClimateTestRecord
from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.domain.enums import ConditionInputMode, EquipmentResource
from climatetest_manager.repositories.climate_tests import ClimateTestRepository
from climatetest_manager.services.climate_tests import (
    ClimateTestService,
    ClimateTestValidationError,
    CreateClimateTestCommand,
    UpdateClimateTestCommand,
)


def _command(**changes: str) -> CreateClimateTestCommand:
    values = {
        "client": "Cliente Exemplo",
        "process_number": "26123.1",
        "product": "Luminária",
        "epl": "Gb",
        "tamb_max_c": "40",
        "delta_t_max_k": "35",
        "selected_option": "B",
        "notes": "Cadastro de teste",
    }
    values.update(changes)
    return CreateClimateTestCommand(**values)


class ClimateTestServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "service.db"
        self.engine = initialize_database(database_path)
        self.session_factory = create_session_factory(self.engine)
        repository = ClimateTestRepository(self.session_factory)
        self.repository = repository
        self.now = datetime(2026, 7, 22, 8, 0)
        self.service = ClimateTestService(repository, now_provider=lambda: self.now)

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temporary_directory.cleanup()

    def test_creates_test_with_rule_snapshot_and_audit(self) -> None:
        test_id = self.service.create(_command())

        with self.session_factory() as session:
            stored = session.scalar(select(ClimateTestRecord))

            self.assertIsNotNone(stored)
            self.assertEqual(stored.id, test_id)
            self.assertEqual(stored.ex_marking, "")
            self.assertEqual(stored.service_temperature_c, Decimal("75.00"))
            self.assertEqual(stored.condition_snapshot.rule_id, "G1-HIGH-B")
            self.assertEqual(stored.condition_snapshot.chamber_duration_hours, 504)
            self.assertEqual(stored.condition_snapshot.drying_temperature_c, Decimal("95.00"))
            self.assertEqual(stored.audit_events[0].actor, "Não identificado")

    def test_accepts_comma_as_decimal_separator(self) -> None:
        self.service.create(_command(tamb_max_c="40,5", delta_t_max_k="29,5", selected_option="A"))

        recent = self.service.list_recent()
        self.assertEqual(recent[0].service_temperature_c, "70.00")
        self.assertEqual(recent[0].selected_option, "A")

    def test_blank_tamb_is_stored_as_positive_40_with_audit_reason(self) -> None:
        self.service.create(_command(tamb_max_c=""))

        with self.session_factory() as session:
            stored = session.scalar(select(ClimateTestRecord))

            self.assertEqual(stored.tamb_max_c, Decimal("40.00"))
            self.assertEqual(stored.service_temperature_c, Decimal("75.00"))
            self.assertIn("adotada conforme Tabela 1", stored.audit_events[0].new_value)

    def test_rejects_missing_required_field(self) -> None:
        with self.assertRaisesRegex(ClimateTestValidationError, "Cliente"):
            self.service.create(_command(client="  "))

    def test_dashboard_starts_without_active_tests(self) -> None:
        self.service.create(_command())

        summary = self.service.dashboard_summary()

        self.assertEqual(summary.in_progress, 0)
        self.assertEqual(summary.drying, 0)

    def test_controls_chamber_tolerance_and_drying_from_actual_start(self) -> None:
        test_id = self.service.create(_command())
        self.service.start_chamber(test_id)

        details = self.service.get_details(test_id)
        self.assertEqual(details.situation, "Na Câmara")
        self.assertEqual(details.chamber_started_at, self.now)
        self.assertEqual(details.chamber_nominal_end_at, self.now + timedelta(hours=504))
        self.assertEqual(details.chamber_maximum_end_at, self.now + timedelta(hours=534))

        self.now = details.chamber_nominal_end_at
        summary = self.service.dashboard_summary()
        self.assertEqual(summary.in_tolerance, 1)
        self.assertEqual(summary.overdue, 0)

        self.service.start_drying(test_id)
        details = self.service.get_details(test_id)
        self.assertEqual(details.situation, "Em Secagem")
        self.assertEqual(details.drying_nominal_end_at, self.now + timedelta(hours=336))
        self.assertEqual(details.drying_maximum_end_at, self.now + timedelta(hours=366))

    def test_does_not_start_drying_before_nominal_chamber_end(self) -> None:
        test_id = self.service.create(_command())
        self.service.start_chamber(test_id)

        with self.assertRaisesRegex(ClimateTestValidationError, "antes do término nominal"):
            self.service.start_drying(test_id)

    def test_cancels_with_reason_and_removes_pending_notifications(self) -> None:
        test_id = self.service.create(_command())
        self.service.start_chamber(test_id)
        self.service.cancel(test_id, "Amostra danificada")

        details = self.service.get_details(test_id)
        self.assertEqual(details.situation, "Cancelado")
        self.assertEqual(details.cancellation_reason, "Amostra danificada")
        self.assertEqual(details.audit_events[-1].actor, "Não identificado")
        self.assertEqual(self.repository.list_due_notifications(self.now + timedelta(days=30)), [])

    def test_accepts_ts_informed_without_tamb_or_delta_t(self) -> None:
        test_id = self.service.create(
            _command(
                input_mode=ConditionInputMode.DIRECT_TS.value,
                tamb_max_c="",
                delta_t_max_k="",
                service_temperature_c="75",
            )
        )

        details = self.service.get_details(test_id)

        self.assertEqual(details.input_mode, ConditionInputMode.DIRECT_TS.value)
        self.assertEqual(details.service_temperature_c, Decimal("75.00"))
        self.assertEqual(details.tamb_max_c, Decimal("0.00"))

    def test_accepts_plan_criterion_without_inventing_exact_ts(self) -> None:
        test_id = self.service.create(
            CreateClimateTestCommand(
                client="Cliente",
                process_number="26124.1",
                product="Invólucro",
                epl="Gb",
                tamb_max_c="",
                delta_t_max_k="",
                selected_option="",
                input_mode=ConditionInputMode.PLAN_CRITERION.value,
                ts_reference="Ts > 70 °C",
                manual_chamber_temperature_c="90",
                manual_chamber_humidity_percent="90",
                manual_chamber_duration_hours="504",
            )
        )

        details = self.service.get_details(test_id)

        self.assertEqual(details.service_temperature_c, Decimal("0.00"))
        self.assertEqual(details.ts_reference, "Ts > 70 °C")
        self.assertEqual(details.selected_option, "-")
        self.assertEqual(details.chamber_duration_hours, 504)

    def test_accepts_direct_configuration_without_epl_or_ts(self) -> None:
        test_id = self.service.create(
            CreateClimateTestCommand(
                client="Cliente",
                process_number="26125.1",
                product="Componente",
                epl="",
                tamb_max_c="",
                delta_t_max_k="",
                selected_option="",
                input_mode=ConditionInputMode.DIRECT_CONFIGURATION.value,
                manual_chamber_temperature_c="80",
                manual_chamber_humidity_percent="90",
                manual_chamber_duration_hours="672",
                sample_quantity="3",
            )
        )

        details = self.service.get_details(test_id)

        self.assertEqual(details.epl, "")
        self.assertEqual(details.service_temperature_c, Decimal("0.00"))
        self.assertEqual(details.sample_quantity, 3)
        self.assertEqual(details.rule_id, "DIRECT-CONFIGURATION")

    def test_edits_started_test_and_recalculates_active_deadline(self) -> None:
        test_id = self.service.create(_command())
        self.service.start_chamber(test_id)

        self.service.update(
            test_id,
            UpdateClimateTestCommand(
                client="Cliente corrigido",
                process_number="26123.1",
                product="Luminária",
                epl="Gb",
                tamb_max_c="40",
                delta_t_max_k="35",
                selected_option="A",
                sample_quantity="2",
                notes="",
                reason="Correção solicitada pelo cliente",
            ),
        )

        details = self.service.get_details(test_id)
        self.assertEqual(details.client, "Cliente corrigido")
        self.assertEqual(details.sample_quantity, 2)
        self.assertEqual(details.chamber_nominal_end_at, self.now + timedelta(hours=336))
        self.assertEqual(details.audit_events[-1].action, "Dados do ensaio corrigidos")
        self.assertIsNotNone(details.audit_events[-1].old_value)

    def test_deletes_only_waiting_registration(self) -> None:
        waiting_id = self.service.create(_command(process_number="26126.1"))
        self.service.delete_waiting(waiting_id)
        with self.assertRaisesRegex(ClimateTestValidationError, "não encontrado"):
            self.service.get_details(waiting_id)

        started_id = self.service.create(_command(process_number="26127.1"))
        self.service.start_chamber(started_id)
        with self.assertRaisesRegex(ClimateTestValidationError, "Somente ensaios"):
            self.service.delete_waiting(started_id)

    def test_allows_audited_registration_correction_after_finish(self) -> None:
        test_id = self.service.create(
            _command(
                delta_t_max_k="20",
                selected_option="A",
            )
        )
        self.service.start_chamber(test_id)
        self.now += timedelta(hours=672)
        self.service.finish(test_id)

        self.service.update(
            test_id,
            UpdateClimateTestCommand(
                client="Cliente corrigido após conclusão",
                process_number="26123.1",
                product="Luminária",
                epl="Gb",
                tamb_max_c="40",
                delta_t_max_k="20",
                selected_option="A",
                sample_quantity="1",
                notes="",
                reason="Correção cadastral após conferência",
            ),
        )

        details = self.service.get_details(test_id)
        self.assertEqual(details.situation, "Finalizado")
        self.assertEqual(details.client, "Cliente corrigido após conclusão")
        self.assertEqual(details.audit_events[-1].reason, "Correção cadastral após conferência")

    def test_pauses_all_chamber_tests_and_shifts_deadlines_on_resume(self) -> None:
        first_id = self.service.create(_command(process_number="26130.1"))
        second_id = self.service.create(_command(process_number="26131.1"))
        self.service.start_chamber(first_id)
        self.service.start_chamber(second_id)
        original_end = self.service.get_details(first_id).chamber_nominal_end_at

        self.now += timedelta(hours=24)
        affected = self.service.pause_resource(
            EquipmentResource.CLIMATE_CHAMBER,
            "Câmara em manutenção",
        )
        self.now += timedelta(hours=48)

        paused = self.service.get_details(first_id)
        self.assertEqual(affected, 2)
        self.assertTrue(paused.is_paused)
        self.assertAlmostEqual(paused.progress_percent, 24 / 504)
        self.assertEqual(
            self.repository.list_due_notifications(self.now + timedelta(days=60)),
            [],
        )

        resumed = self.service.resume_resource(EquipmentResource.CLIMATE_CHAMBER)
        details = self.service.get_details(first_id)

        self.assertEqual(resumed, 2)
        self.assertFalse(details.is_paused)
        self.assertEqual(
            details.chamber_nominal_end_at,
            original_end + timedelta(hours=48),
        )
        self.assertEqual(details.audit_events[-1].action, "Câmara climática retomada")

    def test_resource_pause_blocks_new_stage_until_resume(self) -> None:
        waiting_id = self.service.create(_command(process_number="26132.1"))
        self.service.pause_resource(
            EquipmentResource.CLIMATE_CHAMBER,
            "Indisponível",
        )

        with self.assertRaisesRegex(ClimateTestValidationError, "está pausada"):
            self.service.start_chamber(waiting_id)

        self.service.resume_resource(EquipmentResource.CLIMATE_CHAMBER)
        self.service.start_chamber(waiting_id)
        self.assertEqual(self.service.get_details(waiting_id).situation, "Na Câmara")

    def test_drying_pause_is_independent_from_climate_chamber(self) -> None:
        drying_id = self.service.create(_command(process_number="26132.2"))
        chamber_id = self.service.create(_command(process_number="26132.3"))
        self.service.advance_for_testing(drying_id)
        self.service.advance_for_testing(drying_id)
        self.service.start_chamber(chamber_id)

        affected = self.service.pause_resource(
            EquipmentResource.DRYING,
            "Estufa de secagem em manutenção",
        )

        self.assertEqual(affected, 1)
        self.assertTrue(self.service.get_details(drying_id).is_paused)
        self.assertFalse(self.service.get_details(chamber_id).is_paused)
        statuses = {status.resource: status for status in self.service.resource_statuses()}
        self.assertTrue(statuses[EquipmentResource.DRYING.value].is_paused)
        self.assertFalse(statuses[EquipmentResource.CLIMATE_CHAMBER.value].is_paused)

    def test_changes_chamber_entry_with_reason_and_recalculates_deadline(self) -> None:
        test_id = self.service.create(_command(process_number="26133.1"))
        self.service.start_chamber(test_id)
        corrected_start = self.now - timedelta(hours=2)

        self.service.change_chamber_start(
            test_id,
            corrected_start,
            "Registro lançado duas horas depois",
        )

        details = self.service.get_details(test_id)
        self.assertEqual(details.chamber_started_at, corrected_start)
        self.assertEqual(
            details.chamber_nominal_end_at,
            corrected_start + timedelta(hours=504),
        )
        self.assertEqual(details.audit_events[-1].action, "Entrada da câmara corrigida")
        self.assertEqual(
            details.audit_events[-1].reason,
            "Registro lançado duas horas depois",
        )

    def test_custom_temperature_and_humidity_must_be_between_zero_and_100(self) -> None:
        command = CreateClimateTestCommand(
            client="Cliente",
            process_number="26134.1",
            product="Componente",
            epl="",
            tamb_max_c="",
            delta_t_max_k="",
            selected_option="",
            input_mode=ConditionInputMode.DIRECT_CONFIGURATION.value,
            manual_chamber_temperature_c="101",
            manual_chamber_humidity_percent="90",
            manual_chamber_duration_hours="10000",
        )

        with self.assertRaisesRegex(ClimateTestValidationError, "entre 0 e 100"):
            self.service.create(command)

    def test_dashboard_contains_only_waiting_paused_and_in_progress(self) -> None:
        waiting_id = self.service.create(_command(process_number="26135.1"))
        active_id = self.service.create(_command(process_number="26136.1"))
        cancelled_id = self.service.create(_command(process_number="26137.1"))
        finished_id = self.service.create(
            _command(
                process_number="26138.1",
                delta_t_max_k="20",
                selected_option="A",
            )
        )
        self.service.start_chamber(active_id)
        self.service.cancel(cancelled_id, "Cadastro não será executado")
        self.service.advance_for_testing(finished_id)
        self.service.advance_for_testing(finished_id)

        dashboard_ids = {item.id for item in self.service.list_dashboard_tests()}

        self.assertEqual(dashboard_ids, {waiting_id, active_id})

    def test_test_control_advances_each_stage_without_waiting(self) -> None:
        test_id = self.service.create(_command(process_number="26139.1"))

        self.service.advance_for_testing(test_id)
        self.assertEqual(self.service.get_details(test_id).situation, "Na Câmara")
        self.service.advance_for_testing(test_id)
        self.assertEqual(self.service.get_details(test_id).situation, "Em Secagem")
        self.service.advance_for_testing(test_id)
        details = self.service.get_details(test_id)

        self.assertEqual(details.situation, "Finalizado")
        self.assertEqual(details.audit_events[-1].action, "Etapa avançada para teste")


if __name__ == "__main__":
    unittest.main()
