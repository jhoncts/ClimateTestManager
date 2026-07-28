"""Casos de uso para cadastro e controle operacional dos ensaios climáticos."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from math import ceil

from climatetest_manager.database.models import (
    AuditEvent,
    ClimateConditionSnapshot,
    ClimateTestPauseRecord,
    ClimateTestRecord,
    NotificationEvent,
    ResourcePauseRecord,
)
from climatetest_manager.domain.climate_rules import (
    DEFAULT_TAMB_MAX_C,
    DURATION_POSITIVE_TOLERANCE_HOURS,
    HUMIDITY_TOLERANCE_PERCENT,
    NORMATIVE_RULE_VERSION,
    TEMPERATURE_TOLERANCE_K,
    ClimateCondition,
    PhaseCondition,
    calculate_condition,
    resolve_condition,
)
from climatetest_manager.domain.enums import (
    EPL,
    ConditionInputMode,
    DeadlineCondition,
    EquipmentResource,
    TestOption,
    TestSituation,
)
from climatetest_manager.repositories.climate_tests import (
    AuditHistoryEntry,
    ClimateTestRepository,
    NotificationStatus,
    RecentClimateTest,
)
from climatetest_manager.services.scheduling import classify_deadline

UNIDENTIFIED_ACTOR = "Não identificado"


class ClimateTestValidationError(ValueError):
    """Indica um dado ausente, inválido ou incompatível com o fluxo."""


@dataclass(frozen=True, slots=True)
class CreateClimateTestCommand:
    """Dados informados para cadastrar um ensaio."""

    client: str
    process_number: str
    product: str
    epl: str
    tamb_max_c: str
    delta_t_max_k: str
    selected_option: str
    sample_quantity: str = "1"
    notes: str = ""
    input_mode: str = ConditionInputMode.CALCULATED.value
    service_temperature_c: str = ""
    ts_reference: str = ""
    manual_chamber_temperature_c: str = ""
    manual_chamber_humidity_percent: str = ""
    manual_chamber_duration_hours: str = ""
    manual_drying_required: bool = False
    manual_drying_temperature_c: str = ""
    manual_drying_duration_hours: str = ""


@dataclass(frozen=True, slots=True)
class UpdateClimateTestCommand:
    """Correções cadastrais justificadas para um ensaio existente."""

    client: str
    process_number: str
    product: str
    epl: str
    tamb_max_c: str
    delta_t_max_k: str
    selected_option: str
    sample_quantity: str
    notes: str
    reason: str
    input_mode: str = ConditionInputMode.CALCULATED.value
    service_temperature_c: str = ""
    ts_reference: str = ""
    manual_chamber_temperature_c: str = ""
    manual_chamber_humidity_percent: str = ""
    manual_chamber_duration_hours: str = ""
    manual_drying_required: bool = False
    manual_drying_temperature_c: str = ""
    manual_drying_duration_hours: str = ""


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    """Indicadores operacionais calculados a partir dos registros ativos."""

    in_progress: int
    overdue: int
    due_today: int
    drying: int
    in_tolerance: int
    waiting: int
    paused: int


@dataclass(frozen=True, slots=True)
class ClimateTestListItem:
    """Resumo de um ensaio para pesquisa, filtros e dashboard."""

    id: int
    client: str
    process_number: str
    product: str
    epl: str
    service_temperature_c: Decimal
    ts_reference: str | None
    input_mode: str
    selected_option: str
    sample_quantity: int
    situation: str
    deadline_condition: str | None
    nominal_end_at: datetime | None
    maximum_end_at: datetime | None
    chamber_temperature_c: Decimal
    chamber_humidity_percent: Decimal
    chamber_duration_hours: int
    drying_required: bool
    drying_temperature_c: Decimal | None
    drying_duration_hours: int | None
    is_paused: bool
    paused_at: datetime | None
    pause_reason: str | None
    progress_percent: float
    progress_label: str


@dataclass(frozen=True, slots=True)
class AuditItem:
    """Evento auditável pronto para apresentação."""

    action: str
    actor: str
    occurred_at: datetime
    old_value: str | None
    new_value: str | None
    reason: str | None


@dataclass(frozen=True, slots=True)
class ClimateTestDetails:
    """Visão completa e desacoplada da sessão do banco."""

    id: int
    client: str
    process_number: str
    product: str
    epl: str
    tamb_max_c: Decimal
    delta_t_max_k: Decimal
    service_temperature_c: Decimal
    ts_reference: str | None
    input_mode: str
    selected_option: str
    sample_quantity: int
    situation: str
    deadline_condition: str | None
    notes: str | None
    chamber_temperature_c: Decimal
    chamber_humidity_percent: Decimal
    chamber_duration_hours: int
    chamber_duration_tolerance_hours: int
    chamber_started_at: datetime | None
    chamber_nominal_end_at: datetime | None
    chamber_maximum_end_at: datetime | None
    chamber_ended_at: datetime | None
    drying_required: bool
    drying_temperature_c: Decimal | None
    drying_duration_hours: int | None
    drying_duration_tolerance_hours: int | None
    drying_started_at: datetime | None
    drying_nominal_end_at: datetime | None
    drying_maximum_end_at: datetime | None
    drying_ended_at: datetime | None
    finished_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    rule_id: str
    audit_events: tuple[AuditItem, ...]
    is_paused: bool
    paused_at: datetime | None
    pause_reason: str | None
    progress_percent: float
    progress_label: str


@dataclass(frozen=True, slots=True)
class ResourceStatus:
    """Disponibilidade atual de uma câmara e alcance da eventual parada."""

    resource: str
    label: str
    is_paused: bool
    paused_at: datetime | None
    reason: str | None
    affected_count: int


@dataclass(frozen=True, slots=True)
class AgendaEvent:
    """Prazo operacional exibido na agenda interna."""

    test_id: int
    process_number: str
    client: str
    phase: str
    kind: str
    occurs_at: datetime
    is_paused: bool


def _required(value: str, *, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ClimateTestValidationError(f"Preencha o campo {label}.")
    return normalized


def _numeric_text(value: str) -> str:
    """Aceita a vírgula decimal usada habitualmente no Brasil."""

    return value.strip().replace(",", ".")


def _positive_integer(value: str, *, label: str) -> int:
    normalized = _required(value, label=label)
    if not normalized.isdigit() or int(normalized) < 1:
        raise ClimateTestValidationError(f"{label} deve ser um número inteiro maior que zero.")
    return int(normalized)


def _decimal_input(value: str, *, label: str) -> Decimal:
    try:
        result = Decimal(_numeric_text(_required(value, label=label)))
    except InvalidOperation as error:
        raise ClimateTestValidationError(f"{label} deve ser um número válido.") from error
    if not result.is_finite():
        raise ClimateTestValidationError(f"{label} deve ser um número finito.")
    return result


def _percentage_or_temperature(value: str, *, label: str) -> Decimal:
    result = _decimal_input(value, label=label)
    if not Decimal("0") <= result <= Decimal("100"):
        raise ClimateTestValidationError(f"{label} deve estar entre 0 e 100.")
    return result


@dataclass(frozen=True, slots=True)
class _ResolvedConditionInput:
    condition: ClimateCondition
    mode: ConditionInputMode
    tamb_max_c: Decimal
    delta_t_max_k: Decimal
    ts_reference: str | None
    source_description: str


def _input_mode(value: str) -> ConditionInputMode:
    try:
        mode = ConditionInputMode(value)
    except ValueError as error:
        raise ClimateTestValidationError("Selecione como a condição será definida.") from error
    if mode in {
        ConditionInputMode.PLAN_DEFINED,
        ConditionInputMode.PLAN_CRITERION,
    }:
        return ConditionInputMode.DIRECT_CONFIGURATION
    return mode


def _resolve_condition_input(
    command: CreateClimateTestCommand | UpdateClimateTestCommand,
) -> _ResolvedConditionInput:
    mode = _input_mode(command.input_mode)

    if mode is ConditionInputMode.CALCULATED:
        epl = _required(command.epl, label="EPL")
        option = _required(command.selected_option, label="Opção de ensaio")
        tamb_was_defaulted = not command.tamb_max_c.strip()
        tamb_text = command.tamb_max_c.strip() or str(DEFAULT_TAMB_MAX_C)
        delta_text = _required(command.delta_t_max_k, label="Delta T")
        condition = calculate_condition(
            epl,
            _numeric_text(tamb_text),
            _numeric_text(delta_text),
            option,
        )
        return _ResolvedConditionInput(
            condition=condition,
            mode=mode,
            tamb_max_c=Decimal(_numeric_text(tamb_text)),
            delta_t_max_k=Decimal(_numeric_text(delta_text)),
            ts_reference=None,
            source_description=(
                "Ts calculado a partir de Tamb + Delta T; Tamb +40 °C adotada conforme Tabela 1"
                if tamb_was_defaulted
                else "Ts calculado a partir de Tamb + Delta T"
            ),
        )

    if mode is ConditionInputMode.DIRECT_TS:
        epl = _required(command.epl, label="EPL")
        option = _required(command.selected_option, label="Opção de ensaio")
        ts_text = _required(command.service_temperature_c, label="Ts informado")
        condition = resolve_condition(epl, _numeric_text(ts_text), option)
        return _ResolvedConditionInput(
            condition=condition,
            mode=mode,
            tamb_max_c=Decimal("0"),
            delta_t_max_k=Decimal("0"),
            ts_reference=None,
            source_description="Ts informado diretamente pelo cliente ou plano de ensaio",
        )

    epl_text = command.epl.strip()
    option_text = command.selected_option.strip()
    ts_reference = command.ts_reference.strip() or None
    chamber_temperature = _percentage_or_temperature(
        command.manual_chamber_temperature_c,
        label="Temperatura da câmara",
    )
    chamber_humidity = _percentage_or_temperature(
        command.manual_chamber_humidity_percent,
        label="Umidade da câmara",
    )
    chamber_duration = _positive_integer(
        command.manual_chamber_duration_hours,
        label="Permanência da câmara",
    )
    drying: PhaseCondition | None = None
    if command.manual_drying_required:
        drying = PhaseCondition(
            temperature_c=_percentage_or_temperature(
                command.manual_drying_temperature_c,
                label="Temperatura da secagem",
            ),
            duration_hours=_positive_integer(
                command.manual_drying_duration_hours,
                label="Permanência da secagem",
            ),
            temperature_tolerance_k=TEMPERATURE_TOLERANCE_K,
            duration_positive_tolerance_hours=DURATION_POSITIVE_TOLERANCE_HOURS,
        )
    try:
        normalized_epl = EPL(epl_text) if epl_text else None
        normalized_option = TestOption(option_text) if option_text else None
    except ValueError as error:
        raise ClimateTestValidationError("EPL ou opção de ensaio inválidos.") from error
    condition = ClimateCondition(
        epl=normalized_epl,
        service_temperature_c=Decimal("0"),
        option=normalized_option,
        chamber=PhaseCondition(
            temperature_c=chamber_temperature,
            duration_hours=chamber_duration,
            temperature_tolerance_k=TEMPERATURE_TOLERANCE_K,
            duration_positive_tolerance_hours=DURATION_POSITIVE_TOLERANCE_HOURS,
            humidity_percent=chamber_humidity,
            humidity_tolerance_percent=HUMIDITY_TOLERANCE_PERCENT,
        ),
        drying=drying,
        rule_id="DIRECT-CONFIGURATION",
        normative_rule_version=f"{NORMATIVE_RULE_VERSION}+CONFIGURACAO-DIRETA",
    )
    return _ResolvedConditionInput(
        condition=condition,
        mode=mode,
        tamb_max_c=Decimal("0"),
        delta_t_max_k=Decimal("0"),
        ts_reference=ts_reference,
        source_description="Configuração personalizada informada diretamente",
    )


def _snapshot(condition: ClimateCondition) -> ClimateConditionSnapshot:
    drying = condition.drying
    return ClimateConditionSnapshot(
        rule_id=condition.rule_id,
        normative_rule_version=condition.normative_rule_version,
        option=condition.option.value if condition.option else "-",
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


def _active_pause(record: ClimateTestRecord) -> ClimateTestPauseRecord | None:
    return next(
        (pause for pause in record.pause_intervals if pause.resumed_at is None),
        None,
    )


def _phase_start(record: ClimateTestRecord, phase: str | None = None) -> datetime | None:
    resolved_phase = phase or record.situation
    if resolved_phase == TestSituation.IN_CHAMBER.value:
        return record.chamber_started_at
    if resolved_phase == TestSituation.DRYING.value:
        return record.drying_started_at
    return None


def _phase_deadlines(
    record: ClimateTestRecord,
    now: datetime | None = None,
) -> tuple[datetime | None, datetime | None]:
    if record.situation == TestSituation.IN_CHAMBER.value:
        nominal, maximum = record.chamber_nominal_end_at, record.chamber_maximum_end_at
    elif record.situation == TestSituation.DRYING.value:
        nominal, maximum = record.drying_nominal_end_at, record.drying_maximum_end_at
    else:
        return None, None
    active_pause = _active_pause(record)
    if now is None or active_pause is None or nominal is None or maximum is None:
        return nominal, maximum
    phase_start = _phase_start(record, active_pause.phase)
    pause_start = active_pause.paused_at
    if phase_start is not None:
        pause_start = max(pause_start, phase_start)
    extension = max(now - pause_start, timedelta())
    return nominal + extension, maximum + extension


def _condition(record: ClimateTestRecord, now: datetime) -> DeadlineCondition | None:
    if _active_pause(record) is not None:
        return None
    nominal, maximum = _phase_deadlines(record, now)
    if nominal is None or maximum is None:
        return None
    return classify_deadline(now, nominal, maximum)


def _progress(record: ClimateTestRecord, now: datetime) -> tuple[float, str]:
    """Calcula o tempo efetivamente cumprido, descontando todas as paradas."""

    if record.situation == TestSituation.WAITING.value:
        return 0.0, "Aguardando início"
    snapshot = record.condition_snapshot
    if snapshot is None:
        return 0.0, "Condição indisponível"
    if record.situation == TestSituation.IN_CHAMBER.value:
        phase = TestSituation.IN_CHAMBER.value
        started_at = record.chamber_started_at
        duration_hours = snapshot.chamber_duration_hours
    elif record.situation == TestSituation.DRYING.value:
        phase = TestSituation.DRYING.value
        started_at = record.drying_started_at
        duration_hours = snapshot.drying_duration_hours or 0
    else:
        return 1.0, "Etapa encerrada"
    if started_at is None or duration_hours <= 0:
        return 0.0, "Aguardando início"

    elapsed = max(now - started_at, timedelta())
    for pause in record.pause_intervals:
        if pause.phase != phase:
            continue
        pause_start = max(pause.paused_at, started_at)
        pause_end = pause.resumed_at or now
        if pause_end > pause_start:
            elapsed -= pause_end - pause_start
    elapsed = max(elapsed, timedelta())
    duration = timedelta(hours=duration_hours)
    progress = min(elapsed.total_seconds() / duration.total_seconds(), 1.0)
    remaining_minutes = max(
        0,
        ceil((duration - elapsed).total_seconds() / 60),
    )
    days, remaining_minutes = divmod(remaining_minutes, 24 * 60)
    hours, minutes = divmod(remaining_minutes, 60)
    remaining_parts: list[str] = []
    if days:
        remaining_parts.append(f"{days} d")
    if hours:
        remaining_parts.append(f"{hours} h")
    if minutes and not days:
        remaining_parts.append(f"{minutes} min")
    remaining_text = " ".join(remaining_parts) or "tempo nominal concluído"
    if _active_pause(record) is not None:
        return progress, f"Pausado em {progress * 100:.0f}%"
    return progress, f"{progress * 100:.0f}% • {remaining_text}"


def _completed_pause_duration(
    record: ClimateTestRecord,
    *,
    phase: str,
    started_at: datetime,
) -> timedelta:
    """Soma somente os trechos de pausa concluídos que alcançam a nova entrada."""

    total = timedelta()
    for pause in record.pause_intervals:
        if pause.phase != phase or pause.resumed_at is None:
            continue
        pause_start = max(pause.paused_at, started_at)
        if pause.resumed_at > pause_start:
            total += pause.resumed_at - pause_start
    return total


def _validate_action_time(value: datetime, now: datetime) -> datetime:
    normalized = value.replace(microsecond=0)
    if normalized > now + timedelta(minutes=1):
        raise ClimateTestValidationError("A data e hora não podem estar no futuro.")
    return normalized


def _audit(
    record: ClimateTestRecord,
    action: str,
    *,
    new_value: str | None = None,
    reason: str | None = None,
    actor: str = UNIDENTIFIED_ACTOR,
) -> None:
    record.audit_events.append(
        AuditEvent(
            actor=actor,
            action=action,
            new_value=new_value,
            reason=reason,
        )
    )


def _schedule_notifications(
    record: ClimateTestRecord,
    *,
    phase_key: str,
    phase_label: str,
    nominal_end_at: datetime,
    maximum_end_at: datetime,
) -> None:
    definitions = [
        (
            f"{phase_key}-nominal",
            f"Retirar amostra da {phase_label}",
            (
                f"Ensaio #{record.id} — processo {record.process_number} — "
                f"{record.sample_quantity} amostra(s). "
                "O período nominal terminou e a janela de tolerância foi iniciada."
            ),
            nominal_end_at,
        ),
        (
            f"{phase_key}-maximum",
            f"Limite da {phase_label} atingido",
            (
                f"Ensaio #{record.id} — processo {record.process_number} — "
                f"{record.sample_quantity} amostra(s). "
                "O limite máximo com tolerância de +30 h foi atingido."
            ),
            maximum_end_at,
        ),
    ]
    existing = {item.event_key: item for item in record.notifications}
    for event_key, title, message, scheduled_for_at in definitions:
        event = existing.get(event_key)
        if event is None:
            record.notifications.append(
                NotificationEvent(
                    event_key=event_key,
                    title=title,
                    message=message,
                    scheduled_for_at=scheduled_for_at,
                )
            )
            continue
        event.title = title
        event.message = message
        event.scheduled_for_at = scheduled_for_at
        event.sent_at = None
        event.error_message = None


def _apply_condition_snapshot(
    target: ClimateConditionSnapshot,
    condition: ClimateCondition,
) -> None:
    """Atualiza a fotografia normativa sem trocar sua chave primária."""

    source = _snapshot(condition)
    target.rule_id = source.rule_id
    target.normative_rule_version = source.normative_rule_version
    target.option = source.option
    target.service_temperature_c = source.service_temperature_c
    target.chamber_temperature_c = source.chamber_temperature_c
    target.chamber_temperature_tolerance_k = source.chamber_temperature_tolerance_k
    target.chamber_humidity_percent = source.chamber_humidity_percent
    target.chamber_humidity_tolerance_percent = source.chamber_humidity_tolerance_percent
    target.chamber_duration_hours = source.chamber_duration_hours
    target.chamber_duration_positive_tolerance_hours = (
        source.chamber_duration_positive_tolerance_hours
    )
    target.drying_required = source.drying_required
    target.drying_temperature_c = source.drying_temperature_c
    target.drying_temperature_tolerance_k = source.drying_temperature_tolerance_k
    target.drying_duration_hours = source.drying_duration_hours
    target.drying_duration_positive_tolerance_hours = (
        source.drying_duration_positive_tolerance_hours
    )


def _record_summary(record: ClimateTestRecord) -> str:
    if record.input_mode == ConditionInputMode.CALCULATED.value:
        thermal = (
            f"Tamb={record.tamb_max_c} °C; Delta T={record.delta_t_max_k} K; "
            f"Ts={record.service_temperature_c} °C"
        )
    elif record.input_mode == ConditionInputMode.DIRECT_TS.value:
        thermal = f"Ts informado={record.service_temperature_c} °C"
    elif record.input_mode == ConditionInputMode.PLAN_CRITERION.value:
        thermal = f"critério do plano={record.ts_reference or 'não informado'}"
    else:
        thermal = "configuração direta" + (
            f"; origem={record.ts_reference}" if record.ts_reference else ""
        )
    epl = record.epl or "não informado"
    option = record.selected_option or "não aplicável"
    return (
        f"cliente={record.client}; processo={record.process_number}; produto={record.product}; "
        f"EPL={epl}; {thermal}; opção={option}; "
        f"amostras={record.sample_quantity}"
    )


def _situation_for_resource(resource: EquipmentResource) -> TestSituation:
    if resource is EquipmentResource.CLIMATE_CHAMBER:
        return TestSituation.IN_CHAMBER
    return TestSituation.DRYING


class ClimateTestService:
    """Coordena regras de negócio, fluxo operacional, auditoria e persistência."""

    def __init__(
        self,
        repository: ClimateTestRepository,
        *,
        now_provider: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._repository = repository
        self._now_provider = now_provider

    def _ensure_resource_available(self, resource: EquipmentResource) -> None:
        status = self._repository.get_active_resource_pause(resource)
        if status is not None:
            raise ClimateTestValidationError(
                f"{resource.label} está pausada. Retome o equipamento no Dashboard "
                "antes de avançar esta etapa."
            )

    def create(self, command: CreateClimateTestCommand) -> int:
        """Valida, calcula a condição e grava um novo ensaio aguardando início."""

        client = _required(command.client, label="Cliente")
        process_number = _required(command.process_number, label="Processo")
        product = _required(command.product, label="Produto")
        sample_quantity = _positive_integer(
            command.sample_quantity,
            label="Quantidade de amostras",
        )
        resolved = _resolve_condition_input(command)
        condition = resolved.condition
        climate_test = ClimateTestRecord(
            client=client,
            process_number=process_number,
            product=product,
            ex_marking="",
            epl=condition.epl.value if condition.epl else "",
            tamb_max_c=resolved.tamb_max_c,
            delta_t_max_k=resolved.delta_t_max_k,
            service_temperature_c=condition.service_temperature_c,
            selected_option=condition.option.value if condition.option else None,
            sample_quantity=sample_quantity,
            input_mode=resolved.mode.value,
            ts_reference=resolved.ts_reference,
            situation=TestSituation.WAITING.value,
            notes=command.notes.strip() or None,
            normative_rule_version=condition.normative_rule_version,
            condition_snapshot=_snapshot(condition),
        )
        _audit(
            climate_test,
            "Ensaio cadastrado",
            new_value=(
                f"{resolved.source_description}; "
                f"referência={resolved.ts_reference or f'{condition.service_temperature_c} °C'}; "
                f"opção={condition.option.value if condition.option else 'não aplicável'}; "
                f"amostras={sample_quantity}"
            ),
            reason="Cadastro inicial",
        )
        return self._repository.add(climate_test)

    def update(self, test_id: int, command: UpdateClimateTestCommand) -> None:
        """Corrige dados de ensaio ativo e preserva valores anteriores na auditoria."""

        client = _required(command.client, label="Cliente")
        process_number = _required(command.process_number, label="Processo")
        product = _required(command.product, label="Produto")
        sample_quantity = _positive_integer(
            command.sample_quantity,
            label="Quantidade de amostras",
        )
        reason = _required(command.reason, label="Motivo da alteração")
        resolved = _resolve_condition_input(command)
        condition = resolved.condition

        def operation(record: ClimateTestRecord) -> None:
            snapshot = record.condition_snapshot
            if snapshot is None:
                raise ClimateTestValidationError(
                    "A condição normativa do ensaio não foi encontrada."
                )
            if record.drying_started_at is not None and not condition.requires_drying:
                raise ClimateTestValidationError(
                    "A nova condição não possui secagem, mas essa etapa já foi iniciada. "
                    "Cancele o ensaio com justificativa e faça um novo cadastro."
                )
            if (
                record.finished_at is not None
                and record.drying_started_at is None
                and condition.requires_drying
            ):
                raise ClimateTestValidationError(
                    "A nova condição exige secagem, mas o ensaio foi finalizado sem essa etapa. "
                    "Use uma condição compatível com o que foi realizado."
                )

            old_value = _record_summary(record)
            record.client = client
            record.process_number = process_number
            record.product = product
            record.epl = condition.epl.value if condition.epl else ""
            record.tamb_max_c = resolved.tamb_max_c
            record.delta_t_max_k = resolved.delta_t_max_k
            record.service_temperature_c = condition.service_temperature_c
            record.selected_option = condition.option.value if condition.option else None
            record.sample_quantity = sample_quantity
            record.input_mode = resolved.mode.value
            record.ts_reference = resolved.ts_reference
            record.notes = command.notes.strip() or None
            record.normative_rule_version = condition.normative_rule_version
            _apply_condition_snapshot(snapshot, condition)

            if record.chamber_started_at is not None:
                nominal = (
                    record.chamber_started_at
                    + timedelta(hours=snapshot.chamber_duration_hours)
                    + _completed_pause_duration(
                        record,
                        phase=TestSituation.IN_CHAMBER.value,
                        started_at=record.chamber_started_at,
                    )
                )
                maximum = nominal + timedelta(
                    hours=snapshot.chamber_duration_positive_tolerance_hours
                )
                record.chamber_nominal_end_at = nominal
                record.chamber_maximum_end_at = maximum
            if record.drying_started_at is not None:
                duration = snapshot.drying_duration_hours
                if duration is None:
                    raise ClimateTestValidationError(
                        "A duração da nova condição de secagem não foi encontrada."
                    )
                nominal = (
                    record.drying_started_at
                    + timedelta(hours=duration)
                    + _completed_pause_duration(
                        record,
                        phase=TestSituation.DRYING.value,
                        started_at=record.drying_started_at,
                    )
                )
                maximum = nominal + timedelta(
                    hours=snapshot.drying_duration_positive_tolerance_hours or 0
                )
                record.drying_nominal_end_at = nominal
                record.drying_maximum_end_at = maximum

            if record.situation in {
                TestSituation.IN_CHAMBER.value,
                TestSituation.DRYING.value,
            }:
                if record.situation == TestSituation.IN_CHAMBER.value:
                    if (
                        record.chamber_nominal_end_at is None
                        or record.chamber_maximum_end_at is None
                    ):
                        raise ClimateTestValidationError(
                            "Os prazos atualizados da câmara não foram calculados."
                        )
                    _schedule_notifications(
                        record,
                        phase_key="chamber",
                        phase_label="câmara",
                        nominal_end_at=record.chamber_nominal_end_at,
                        maximum_end_at=record.chamber_maximum_end_at,
                    )
                else:
                    if record.drying_nominal_end_at is None or record.drying_maximum_end_at is None:
                        raise ClimateTestValidationError(
                            "Os prazos atualizados da secagem não foram calculados."
                        )
                    _schedule_notifications(
                        record,
                        phase_key="drying",
                        phase_label="secagem",
                        nominal_end_at=record.drying_nominal_end_at,
                        maximum_end_at=record.drying_maximum_end_at,
                    )

            _audit(
                record,
                "Dados do ensaio corrigidos",
                new_value=_record_summary(record),
                reason=reason,
            )
            record.audit_events[-1].old_value = old_value

        self._repository.mutate(test_id, operation)

    def delete_waiting(self, test_id: int) -> None:
        """Exclui somente cadastros que ainda não produziram execução operacional."""

        record = self._repository.get(test_id)
        if record is None:
            raise ClimateTestValidationError(f"Ensaio #{test_id} não encontrado.")
        if record.situation != TestSituation.WAITING.value:
            raise ClimateTestValidationError(
                "Somente ensaios ainda aguardando podem ser excluídos. "
                "Se a câmara já foi iniciada, cancele o ensaio e informe o motivo."
            )
        self._repository.delete(test_id)

    def start_chamber(self, test_id: int, started_at: datetime | None = None) -> None:
        """Inicia a câmara agora ou na data real informada manualmente."""

        self._ensure_resource_available(EquipmentResource.CLIMATE_CHAMBER)
        now = self._now_provider().replace(microsecond=0)
        effective_start = _validate_action_time(started_at or now, now)

        def operation(record: ClimateTestRecord) -> None:
            if record.situation != TestSituation.WAITING.value:
                raise ClimateTestValidationError(
                    "Somente ensaios aguardando podem iniciar a câmara."
                )
            snapshot = record.condition_snapshot
            if snapshot is None:
                raise ClimateTestValidationError(
                    "A condição normativa do ensaio não foi encontrada."
                )
            nominal = effective_start + timedelta(hours=snapshot.chamber_duration_hours)
            maximum = nominal + timedelta(hours=snapshot.chamber_duration_positive_tolerance_hours)
            record.chamber_started_at = effective_start
            record.chamber_nominal_end_at = nominal
            record.chamber_maximum_end_at = maximum
            record.situation = TestSituation.IN_CHAMBER.value
            _schedule_notifications(
                record,
                phase_key="chamber",
                phase_label="câmara",
                nominal_end_at=nominal,
                maximum_end_at=maximum,
            )
            _audit(
                record,
                "Câmara iniciada",
                new_value=f"Entrada: {effective_start.isoformat(sep=' ', timespec='minutes')}",
                reason="Início operacional",
            )

        self._repository.mutate(test_id, operation)

    def start_drying(self, test_id: int, started_at: datetime | None = None) -> None:
        """Registra a retirada da câmara e inicia a secagem a partir do instante real."""

        self._ensure_resource_available(EquipmentResource.CLIMATE_CHAMBER)
        self._ensure_resource_available(EquipmentResource.DRYING)
        now = self._now_provider().replace(microsecond=0)
        effective_start = _validate_action_time(started_at or now, now)

        def operation(record: ClimateTestRecord) -> None:
            if _active_pause(record) is not None:
                raise ClimateTestValidationError(
                    "A contagem desta etapa está pausada. Retome o equipamento antes "
                    "de finalizar ou avançar o ensaio."
                )
            snapshot = record.condition_snapshot
            if record.situation != TestSituation.IN_CHAMBER.value:
                raise ClimateTestValidationError("O ensaio não está na câmara.")
            if snapshot is None or not snapshot.drying_required:
                raise ClimateTestValidationError("Este ensaio não possui etapa de secagem.")
            if record.chamber_nominal_end_at and effective_start < record.chamber_nominal_end_at:
                raise ClimateTestValidationError(
                    "A secagem não pode começar antes do término nominal da câmara."
                )
            if snapshot.drying_duration_hours is None:
                raise ClimateTestValidationError("A duração da secagem não foi encontrada.")
            tolerance = snapshot.drying_duration_positive_tolerance_hours or 0
            nominal = effective_start + timedelta(hours=snapshot.drying_duration_hours)
            maximum = nominal + timedelta(hours=tolerance)
            record.chamber_ended_at = effective_start
            record.drying_started_at = effective_start
            record.drying_nominal_end_at = nominal
            record.drying_maximum_end_at = maximum
            record.situation = TestSituation.DRYING.value
            record.notifications[:] = [
                item
                for item in record.notifications
                if item.sent_at is not None or not item.event_key.startswith("chamber-")
            ]
            _schedule_notifications(
                record,
                phase_key="drying",
                phase_label="secagem",
                nominal_end_at=nominal,
                maximum_end_at=maximum,
            )
            _audit(
                record,
                "Secagem iniciada",
                new_value=f"Entrada: {effective_start.isoformat(sep=' ', timespec='minutes')}",
                reason="Retirada da câmara e início da secagem",
            )

        self._repository.mutate(test_id, operation)

    def finish(self, test_id: int, finished_at: datetime | None = None) -> None:
        """Finaliza um ensaio após o período nominal da sua etapa ativa."""

        now = self._now_provider().replace(microsecond=0)
        effective_end = _validate_action_time(finished_at or now, now)

        def operation(record: ClimateTestRecord) -> None:
            if _active_pause(record) is not None:
                raise ClimateTestValidationError(
                    "A contagem desta etapa está pausada. Retome o equipamento antes "
                    "de finalizar o ensaio."
                )
            snapshot = record.condition_snapshot
            if record.situation == TestSituation.IN_CHAMBER.value:
                if snapshot is not None and snapshot.drying_required:
                    raise ClimateTestValidationError(
                        "Inicie a secagem antes de finalizar o ensaio."
                    )
                nominal = record.chamber_nominal_end_at
                record.chamber_ended_at = effective_end
            elif record.situation == TestSituation.DRYING.value:
                nominal = record.drying_nominal_end_at
                record.drying_ended_at = effective_end
            else:
                raise ClimateTestValidationError(
                    "O ensaio não possui uma etapa ativa para finalizar."
                )
            if nominal is not None and effective_end < nominal:
                raise ClimateTestValidationError(
                    "O ensaio não pode ser finalizado antes do término nominal da etapa."
                )
            record.finished_at = effective_end
            record.situation = TestSituation.FINISHED.value
            record.notifications[:] = [
                item for item in record.notifications if item.sent_at is not None
            ]
            _audit(
                record,
                "Ensaio finalizado",
                new_value=f"Saída: {effective_end.isoformat(sep=' ', timespec='minutes')}",
                reason="Conclusão operacional",
            )

        self._repository.mutate(test_id, operation)

    def cancel(self, test_id: int, reason: str) -> None:
        """Cancela um ensaio não concluído e exige justificativa auditável."""

        normalized_reason = _required(reason, label="Motivo do cancelamento")
        cancelled_at = self._now_provider().replace(microsecond=0)

        def operation(record: ClimateTestRecord) -> None:
            if record.situation in {
                TestSituation.FINISHED.value,
                TestSituation.CANCELLED.value,
            }:
                raise ClimateTestValidationError("Este ensaio não pode mais ser cancelado.")
            record.cancelled_at = cancelled_at
            record.cancellation_reason = normalized_reason
            record.situation = TestSituation.CANCELLED.value
            record.notifications[:] = [item for item in record.notifications if item.sent_at]
            _audit(
                record,
                "Ensaio cancelado",
                new_value=TestSituation.CANCELLED.value,
                reason=normalized_reason,
            )

        self._repository.mutate(test_id, operation)

    def change_chamber_start(
        self,
        test_id: int,
        started_at: datetime,
        reason: str,
    ) -> None:
        """Corrige a entrada da câmara e recalcula os prazos com auditoria."""

        now = self._now_provider().replace(microsecond=0)
        effective_start = _validate_action_time(started_at, now)
        normalized_reason = _required(reason, label="Motivo da alteração")

        def operation(record: ClimateTestRecord) -> None:
            if record.chamber_started_at is None or record.condition_snapshot is None:
                raise ClimateTestValidationError("A entrada da câmara ainda não foi registrada.")
            if record.chamber_ended_at is not None and effective_start > record.chamber_ended_at:
                raise ClimateTestValidationError(
                    "A entrada da câmara não pode ser posterior à retirada registrada."
                )
            old_start = record.chamber_started_at
            snapshot = record.condition_snapshot
            nominal = (
                effective_start
                + timedelta(hours=snapshot.chamber_duration_hours)
                + _completed_pause_duration(
                    record,
                    phase=TestSituation.IN_CHAMBER.value,
                    started_at=effective_start,
                )
            )
            maximum = nominal + timedelta(hours=snapshot.chamber_duration_positive_tolerance_hours)
            record.chamber_started_at = effective_start
            record.chamber_nominal_end_at = nominal
            record.chamber_maximum_end_at = maximum
            if record.situation == TestSituation.IN_CHAMBER.value:
                _schedule_notifications(
                    record,
                    phase_key="chamber",
                    phase_label="câmara",
                    nominal_end_at=nominal,
                    maximum_end_at=maximum,
                )
            _audit(
                record,
                "Entrada da câmara corrigida",
                new_value=effective_start.isoformat(sep=" ", timespec="minutes"),
                reason=normalized_reason,
            )
            record.audit_events[-1].old_value = old_start.isoformat(
                sep=" ",
                timespec="minutes",
            )

        self._repository.mutate(test_id, operation)

    def pause_resource(self, resource: str | EquipmentResource, reason: str) -> int:
        """Pausa um equipamento e congela todos os ensaios ativos nele."""

        try:
            resolved_resource = EquipmentResource(resource)
        except ValueError as error:
            raise ClimateTestValidationError("Equipamento inválido para pausa.") from error
        normalized_reason = _required(reason, label="Motivo da pausa")
        paused_at = self._now_provider().replace(microsecond=0)
        affected_count = 0

        def operation(session, active_pause, records) -> None:
            nonlocal affected_count
            if active_pause is not None:
                raise ClimateTestValidationError(f"{resolved_resource.label} já está pausada.")
            pause = ResourcePauseRecord(
                resource=resolved_resource.value,
                reason=normalized_reason,
                paused_at=paused_at,
            )
            session.add(pause)
            for record in records:
                link = ClimateTestPauseRecord(
                    climate_test=record,
                    resource_pause=pause,
                    phase=record.situation,
                    paused_at=paused_at,
                )
                session.add(link)
                _audit(
                    record,
                    f"{resolved_resource.label} pausada",
                    new_value=paused_at.isoformat(sep=" ", timespec="minutes"),
                    reason=normalized_reason,
                )
            affected_count = len(records)

        self._repository.mutate_resource_state(
            resolved_resource,
            _situation_for_resource(resolved_resource),
            operation,
        )
        return affected_count

    def resume_resource(self, resource: str | EquipmentResource) -> int:
        """Retoma um equipamento e desloca cada prazo pelo intervalo parado."""

        try:
            resolved_resource = EquipmentResource(resource)
        except ValueError as error:
            raise ClimateTestValidationError("Equipamento inválido para retomada.") from error
        resumed_at = self._now_provider().replace(microsecond=0)
        affected_count = 0

        def operation(_session, active_pause, _records) -> None:
            nonlocal affected_count
            if active_pause is None:
                raise ClimateTestValidationError(f"{resolved_resource.label} não está pausada.")
            if resumed_at < active_pause.paused_at:
                raise ClimateTestValidationError(
                    "A retomada não pode ser anterior ao início da pausa."
                )
            active_pause.resumed_at = resumed_at
            for link in active_pause.affected_tests:
                record = link.climate_test
                phase_start = _phase_start(record, link.phase)
                effective_pause_start = link.paused_at
                if phase_start is not None:
                    effective_pause_start = max(effective_pause_start, phase_start)
                duration = max(resumed_at - effective_pause_start, timedelta())
                link.resumed_at = resumed_at
                if record.situation == link.phase:
                    if link.phase == TestSituation.IN_CHAMBER.value:
                        if record.chamber_nominal_end_at is not None:
                            record.chamber_nominal_end_at += duration
                        if record.chamber_maximum_end_at is not None:
                            record.chamber_maximum_end_at += duration
                        nominal = record.chamber_nominal_end_at
                        maximum = record.chamber_maximum_end_at
                        phase_key = "chamber"
                        phase_label = "câmara"
                    else:
                        if record.drying_nominal_end_at is not None:
                            record.drying_nominal_end_at += duration
                        if record.drying_maximum_end_at is not None:
                            record.drying_maximum_end_at += duration
                        nominal = record.drying_nominal_end_at
                        maximum = record.drying_maximum_end_at
                        phase_key = "drying"
                        phase_label = "secagem"
                    if nominal is not None and maximum is not None:
                        _schedule_notifications(
                            record,
                            phase_key=phase_key,
                            phase_label=phase_label,
                            nominal_end_at=nominal,
                            maximum_end_at=maximum,
                        )
                _audit(
                    record,
                    f"{resolved_resource.label} retomada",
                    new_value=(f"Pausa encerrada após {int(duration.total_seconds())} segundo(s)"),
                    reason=active_pause.reason,
                )
                affected_count += 1

        self._repository.mutate_resource_state(
            resolved_resource,
            _situation_for_resource(resolved_resource),
            operation,
        )
        return affected_count

    def advance_for_testing(self, test_id: int) -> None:
        """Avança uma etapa sem esperar o prazo; uso exclusivo da validação manual."""

        record = self._repository.get(test_id)
        if record is None:
            raise ClimateTestValidationError(f"Ensaio #{test_id} não encontrado.")
        if record.situation == TestSituation.WAITING.value:
            self._ensure_resource_available(EquipmentResource.CLIMATE_CHAMBER)
        elif record.situation == TestSituation.IN_CHAMBER.value:
            self._ensure_resource_available(EquipmentResource.CLIMATE_CHAMBER)
            if record.condition_snapshot and record.condition_snapshot.drying_required:
                self._ensure_resource_available(EquipmentResource.DRYING)
        elif record.situation == TestSituation.DRYING.value:
            self._ensure_resource_available(EquipmentResource.DRYING)
        else:
            raise ClimateTestValidationError(
                "O ensaio já está encerrado e não possui próxima etapa."
            )
        now = self._now_provider().replace(microsecond=0)

        def operation(target: ClimateTestRecord) -> None:
            if _active_pause(target) is not None:
                raise ClimateTestValidationError(
                    "Retome o equipamento antes de usar o avanço de teste."
                )
            snapshot = target.condition_snapshot
            if snapshot is None:
                raise ClimateTestValidationError(
                    "A condição normativa do ensaio não foi encontrada."
                )
            old_situation = target.situation
            if target.situation == TestSituation.WAITING.value:
                target.chamber_started_at = now
                target.chamber_nominal_end_at = now + timedelta(
                    hours=snapshot.chamber_duration_hours
                )
                target.chamber_maximum_end_at = target.chamber_nominal_end_at + timedelta(
                    hours=snapshot.chamber_duration_positive_tolerance_hours
                )
                target.situation = TestSituation.IN_CHAMBER.value
                _schedule_notifications(
                    target,
                    phase_key="chamber",
                    phase_label="câmara",
                    nominal_end_at=target.chamber_nominal_end_at,
                    maximum_end_at=target.chamber_maximum_end_at,
                )
            elif target.situation == TestSituation.IN_CHAMBER.value:
                target.chamber_ended_at = now
                target.notifications[:] = [
                    item
                    for item in target.notifications
                    if item.sent_at is not None or not item.event_key.startswith("chamber-")
                ]
                if snapshot.drying_required:
                    duration = snapshot.drying_duration_hours or 0
                    tolerance = snapshot.drying_duration_positive_tolerance_hours or 0
                    target.drying_started_at = now
                    target.drying_nominal_end_at = now + timedelta(hours=duration)
                    target.drying_maximum_end_at = target.drying_nominal_end_at + timedelta(
                        hours=tolerance
                    )
                    target.situation = TestSituation.DRYING.value
                    _schedule_notifications(
                        target,
                        phase_key="drying",
                        phase_label="secagem",
                        nominal_end_at=target.drying_nominal_end_at,
                        maximum_end_at=target.drying_maximum_end_at,
                    )
                else:
                    target.finished_at = now
                    target.situation = TestSituation.FINISHED.value
            else:
                target.drying_ended_at = now
                target.finished_at = now
                target.situation = TestSituation.FINISHED.value
                target.notifications[:] = [
                    item for item in target.notifications if item.sent_at is not None
                ]
            _audit(
                target,
                "Etapa avançada para teste",
                new_value=f"{old_situation} → {target.situation}",
                reason="Ferramenta temporária de validação da v0.4.0",
            )

        self._repository.mutate(test_id, operation)

    def dashboard_summary(self) -> DashboardSummary:
        """Calcula indicadores reais com base na etapa e nos prazos persistidos."""

        items = self.list_tests()
        active = {
            TestSituation.IN_CHAMBER.value,
            TestSituation.DRYING.value,
        }
        return DashboardSummary(
            in_progress=sum(item.situation in active and not item.is_paused for item in items),
            overdue=sum(
                item.deadline_condition == DeadlineCondition.OVERDUE.value for item in items
            ),
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

    def list_recent(self) -> list[RecentClimateTest]:
        """Fornece os últimos ensaios ao dashboard."""

        return self._repository.list_recent()

    def list_tests(self) -> list[ClimateTestListItem]:
        """Lista todos os ensaios com a condição de prazo calculada no instante da consulta."""

        now = self._now_provider().replace(microsecond=0)
        result: list[ClimateTestListItem] = []
        for record in self._repository.list_records():
            deadline = _condition(record, now)
            nominal, maximum = _phase_deadlines(record, now)
            snapshot = record.condition_snapshot
            if snapshot is None:
                continue
            active_pause = _active_pause(record)
            progress, progress_label = _progress(record, now)
            result.append(
                ClimateTestListItem(
                    id=record.id,
                    client=record.client,
                    process_number=record.process_number,
                    product=record.product,
                    epl=record.epl,
                    service_temperature_c=record.service_temperature_c,
                    ts_reference=record.ts_reference,
                    input_mode=record.input_mode,
                    selected_option=record.selected_option or "-",
                    sample_quantity=record.sample_quantity,
                    situation=record.situation,
                    deadline_condition=deadline.value if deadline else None,
                    nominal_end_at=nominal,
                    maximum_end_at=maximum,
                    chamber_temperature_c=snapshot.chamber_temperature_c,
                    chamber_humidity_percent=snapshot.chamber_humidity_percent,
                    chamber_duration_hours=snapshot.chamber_duration_hours,
                    drying_required=snapshot.drying_required,
                    drying_temperature_c=snapshot.drying_temperature_c,
                    drying_duration_hours=snapshot.drying_duration_hours,
                    is_paused=active_pause is not None,
                    paused_at=active_pause.paused_at if active_pause else None,
                    pause_reason=(
                        active_pause.resource_pause.reason
                        if active_pause and active_pause.resource_pause
                        else None
                    ),
                    progress_percent=progress,
                    progress_label=progress_label,
                )
            )
        return result

    def list_dashboard_tests(self) -> list[ClimateTestListItem]:
        """Lista apenas cadastros que ainda exigem acompanhamento operacional."""

        active_situations = {
            TestSituation.WAITING.value,
            TestSituation.IN_CHAMBER.value,
            TestSituation.DRYING.value,
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

    def resource_statuses(self) -> tuple[ResourceStatus, ...]:
        """Fornece os dois controles globais apresentados no Dashboard."""

        result: list[ResourceStatus] = []
        for resource in EquipmentResource:
            pause = self._repository.get_active_resource_pause(resource)
            result.append(
                ResourceStatus(
                    resource=resource.value,
                    label=resource.label,
                    is_paused=pause is not None,
                    paused_at=pause.paused_at if pause else None,
                    reason=pause.reason if pause else None,
                    affected_count=pause.affected_count if pause else 0,
                )
            )
        return tuple(result)

    def list_agenda_events(self) -> list[AgendaEvent]:
        """Monta a agenda interna usando somente prazos de ensaios ativos."""

        events: list[AgendaEvent] = []
        for item in self.list_dashboard_tests():
            if item.situation == TestSituation.WAITING.value:
                continue
            phase = (
                "Câmara climática"
                if item.situation == TestSituation.IN_CHAMBER.value
                else "Secagem"
            )
            if item.nominal_end_at is not None:
                events.append(
                    AgendaEvent(
                        test_id=item.id,
                        process_number=item.process_number,
                        client=item.client,
                        phase=phase,
                        kind="Retirar a partir de",
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
                        kind="Limite para retirada",
                        occurs_at=item.maximum_end_at,
                        is_paused=item.is_paused,
                    )
                )
        return sorted(events, key=lambda item: (item.occurs_at, item.test_id, item.kind))

    def get_details(self, test_id: int) -> ClimateTestDetails:
        """Obtém dados completos e o histórico de um ensaio."""

        record = self._repository.get(test_id)
        if record is None or record.condition_snapshot is None:
            raise ClimateTestValidationError(f"Ensaio #{test_id} não encontrado.")
        snapshot = record.condition_snapshot
        now = self._now_provider().replace(microsecond=0)
        deadline = _condition(record, now)
        active_pause = _active_pause(record)
        progress, progress_label = _progress(record, now)
        chamber_nominal = record.chamber_nominal_end_at
        chamber_maximum = record.chamber_maximum_end_at
        drying_nominal = record.drying_nominal_end_at
        drying_maximum = record.drying_maximum_end_at
        effective_nominal, effective_maximum = _phase_deadlines(record, now)
        if record.situation == TestSituation.IN_CHAMBER.value:
            chamber_nominal, chamber_maximum = effective_nominal, effective_maximum
        elif record.situation == TestSituation.DRYING.value:
            drying_nominal, drying_maximum = effective_nominal, effective_maximum
        audit_events = tuple(
            AuditItem(
                action=event.action,
                actor=event.actor,
                occurred_at=event.occurred_at,
                old_value=event.old_value,
                new_value=event.new_value,
                reason=event.reason,
            )
            for event in sorted(record.audit_events, key=lambda item: (item.occurred_at, item.id))
        )
        return ClimateTestDetails(
            id=record.id,
            client=record.client,
            process_number=record.process_number,
            product=record.product,
            epl=record.epl,
            tamb_max_c=record.tamb_max_c,
            delta_t_max_k=record.delta_t_max_k,
            service_temperature_c=record.service_temperature_c,
            ts_reference=record.ts_reference,
            input_mode=record.input_mode,
            selected_option=record.selected_option or "-",
            sample_quantity=record.sample_quantity,
            situation=record.situation,
            deadline_condition=deadline.value if deadline else None,
            notes=record.notes,
            chamber_temperature_c=snapshot.chamber_temperature_c,
            chamber_humidity_percent=snapshot.chamber_humidity_percent,
            chamber_duration_hours=snapshot.chamber_duration_hours,
            chamber_duration_tolerance_hours=(snapshot.chamber_duration_positive_tolerance_hours),
            chamber_started_at=record.chamber_started_at,
            chamber_nominal_end_at=chamber_nominal,
            chamber_maximum_end_at=chamber_maximum,
            chamber_ended_at=record.chamber_ended_at,
            drying_required=snapshot.drying_required,
            drying_temperature_c=snapshot.drying_temperature_c,
            drying_duration_hours=snapshot.drying_duration_hours,
            drying_duration_tolerance_hours=(snapshot.drying_duration_positive_tolerance_hours),
            drying_started_at=record.drying_started_at,
            drying_nominal_end_at=drying_nominal,
            drying_maximum_end_at=drying_maximum,
            drying_ended_at=record.drying_ended_at,
            finished_at=record.finished_at,
            cancelled_at=record.cancelled_at,
            cancellation_reason=record.cancellation_reason,
            rule_id=snapshot.rule_id,
            audit_events=audit_events,
            is_paused=active_pause is not None,
            paused_at=active_pause.paused_at if active_pause else None,
            pause_reason=(
                active_pause.resource_pause.reason
                if active_pause and active_pause.resource_pause
                else None
            ),
            progress_percent=progress,
            progress_label=progress_label,
        )

    def list_history(self) -> list[AuditHistoryEntry]:
        """Fornece a trilha global de auditoria."""

        return self._repository.list_audit_history()

    def notification_status(self) -> NotificationStatus:
        """Fornece o diagnóstico mais recente do agente local."""

        return self._repository.get_notification_status()
