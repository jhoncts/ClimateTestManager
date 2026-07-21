"""Casos de uso para cadastro e consulta dos ensaios climáticos."""

import getpass
from dataclasses import dataclass
from decimal import Decimal

from climatetest_manager.database.models import (
    AuditEvent,
    ClimateConditionSnapshot,
    ClimateTestRecord,
)
from climatetest_manager.domain.climate_rules import (
    DEFAULT_TAMB_MAX_C,
    ClimateCondition,
    calculate_condition,
)
from climatetest_manager.domain.enums import TestSituation
from climatetest_manager.repositories.climate_tests import (
    ClimateTestRepository,
    RecentClimateTest,
)


class ClimateTestValidationError(ValueError):
    """Indica um dado de cadastro ausente ou inválido."""


@dataclass(frozen=True, slots=True)
class CreateClimateTestCommand:
    """Dados informados pelo operador para cadastrar um ensaio."""

    client: str
    process_number: str
    product: str
    ex_marking: str
    epl: str
    tamb_max_c: str
    delta_t_max_k: str
    selected_option: str
    notes: str = ""


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    """Indicadores que já podem ser calculados no estágio atual do fluxo."""

    in_progress: int
    overdue: int
    due_today: int
    drying: int


def _required(value: str, *, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ClimateTestValidationError(f"Preencha o campo {label}.")
    return normalized


def _numeric_text(value: str) -> str:
    """Aceita a vírgula decimal usada habitualmente no Brasil."""

    return value.strip().replace(",", ".")


def _snapshot(condition: ClimateCondition) -> ClimateConditionSnapshot:
    drying = condition.drying
    return ClimateConditionSnapshot(
        rule_id=condition.rule_id,
        normative_rule_version=condition.normative_rule_version,
        option=condition.option.value,
        service_temperature_c=condition.service_temperature_c,
        chamber_temperature_c=condition.chamber.temperature_c,
        chamber_temperature_tolerance_k=condition.chamber.temperature_tolerance_k,
        chamber_humidity_percent=condition.chamber.humidity_percent or Decimal("0"),
        chamber_humidity_tolerance_percent=(
            condition.chamber.humidity_tolerance_percent or Decimal("0")
        ),
        chamber_duration_hours=condition.chamber.duration_hours,
        chamber_duration_positive_tolerance_hours=(
            condition.chamber.duration_positive_tolerance_hours
        ),
        drying_required=condition.requires_drying,
        drying_temperature_c=drying.temperature_c if drying else None,
        drying_temperature_tolerance_k=(drying.temperature_tolerance_k if drying else None),
        drying_duration_hours=drying.duration_hours if drying else None,
        drying_duration_positive_tolerance_hours=(
            drying.duration_positive_tolerance_hours if drying else None
        ),
    )


class ClimateTestService:
    """Coordena regras de negócio, auditoria e persistência."""

    def __init__(self, repository: ClimateTestRepository) -> None:
        self._repository = repository

    def create(self, command: CreateClimateTestCommand, *, actor: str | None = None) -> int:
        """Valida, calcula a condição e grava o novo ensaio."""

        client = _required(command.client, label="Cliente")
        process_number = _required(command.process_number, label="Processo")
        product = _required(command.product, label="Produto")
        ex_marking = _required(command.ex_marking, label="Marcação Ex")
        epl = _required(command.epl, label="EPL")
        tamb_was_defaulted = not command.tamb_max_c.strip()
        tamb_max_c = command.tamb_max_c.strip() or str(DEFAULT_TAMB_MAX_C)
        delta_t_max_k = _required(command.delta_t_max_k, label="Delta T")
        selected_option = _required(command.selected_option, label="Opção de ensaio")
        normalized_tamb_max_c = _numeric_text(tamb_max_c)

        condition = calculate_condition(
            epl,
            normalized_tamb_max_c,
            _numeric_text(delta_t_max_k),
            selected_option,
        )
        tamb_max_decimal = Decimal(normalized_tamb_max_c)
        climate_test = ClimateTestRecord(
            client=client,
            process_number=process_number,
            product=product,
            ex_marking=ex_marking,
            epl=condition.epl.value,
            tamb_max_c=tamb_max_decimal,
            delta_t_max_k=Decimal(_numeric_text(delta_t_max_k)),
            service_temperature_c=condition.service_temperature_c,
            selected_option=condition.option.value,
            situation=TestSituation.WAITING.value,
            notes=command.notes.strip() or None,
            normative_rule_version=condition.normative_rule_version,
            condition_snapshot=_snapshot(condition),
        )
        tamb_audit_value = f"{tamb_max_decimal} °C"
        if tamb_was_defaulted:
            tamb_audit_value += " (adotada conforme Tabela 1)"
        climate_test.audit_events.append(
            AuditEvent(
                actor=(actor or getpass.getuser() or "Operador local"),
                action="Ensaio cadastrado",
                new_value=(
                    f"Tamb={tamb_audit_value}; Ts={condition.service_temperature_c} °C; "
                    f"opção={condition.option.value}; regra={condition.rule_id}"
                ),
                reason="Cadastro inicial",
            )
        )
        return self._repository.add(climate_test)

    def dashboard_summary(self) -> DashboardSummary:
        """Consulta os indicadores já suportados pelas etapas implementadas."""

        in_progress = self._repository.count_by_situations(
            TestSituation.IN_CHAMBER, TestSituation.DRYING
        )
        drying = self._repository.count_by_situations(TestSituation.DRYING)
        return DashboardSummary(
            in_progress=in_progress,
            overdue=0,
            due_today=0,
            drying=drying,
        )

    def list_recent(self) -> list[RecentClimateTest]:
        """Fornece os últimos ensaios ao dashboard."""

        return self._repository.list_recent()
