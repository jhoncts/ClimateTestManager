"""Motor determinístico da Tabela 17 da ABNT NBR IEC 60079-0:2020."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from climatetest_manager.domain.enums import EPL, TestOption

type NumericInput = Decimal | int | float | str

NORMATIVE_RULE_VERSION = "IEC60079-0:2020-T17-v1"
TEMPERATURE_TOLERANCE_K = Decimal("2")
HUMIDITY_PERCENT = Decimal("90")
HUMIDITY_TOLERANCE_PERCENT = Decimal("5")
DURATION_POSITIVE_TOLERANCE_HOURS = 30


class ClimateRuleError(ValueError):
    """Indica que a condição recebida não pode ser calculada com segurança."""


@dataclass(frozen=True, slots=True)
class PhaseCondition:
    """Condição nominal e tolerâncias de uma etapa do ensaio."""

    temperature_c: Decimal
    duration_hours: int
    temperature_tolerance_k: Decimal = TEMPERATURE_TOLERANCE_K
    duration_positive_tolerance_hours: int = DURATION_POSITIVE_TOLERANCE_HOURS
    humidity_percent: Decimal | None = None
    humidity_tolerance_percent: Decimal | None = None

    @property
    def maximum_duration_hours(self) -> int:
        """Limite superior permitido para a duração da etapa."""

        return self.duration_hours + self.duration_positive_tolerance_hours


@dataclass(frozen=True, slots=True)
class ClimateCondition:
    """Resultado completo de uma consulta à regra normativa."""

    epl: EPL
    service_temperature_c: Decimal
    option: TestOption
    chamber: PhaseCondition
    drying: PhaseCondition | None
    rule_id: str
    normative_rule_version: str = NORMATIVE_RULE_VERSION

    @property
    def requires_drying(self) -> bool:
        return self.drying is not None

    @property
    def nominal_total_hours(self) -> int:
        drying_hours = self.drying.duration_hours if self.drying else 0
        return self.chamber.duration_hours + drying_hours


def _decimal(value: NumericInput, *, field_name: str) -> Decimal:
    """Converte entradas externas sem introduzir imprecisão binária adicional."""

    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ClimateRuleError(f"{field_name} deve ser um número válido.") from error

    if not result.is_finite():
        raise ClimateRuleError(f"{field_name} deve ser um número finito.")
    return result


def _epl(value: EPL | str) -> EPL:
    try:
        return value if isinstance(value, EPL) else EPL(value)
    except ValueError as error:
        valid_values = ", ".join(item.value for item in EPL)
        raise ClimateRuleError(f"EPL inválido. Valores aceitos: {valid_values}.") from error


def _option(value: TestOption | str) -> TestOption:
    try:
        return value if isinstance(value, TestOption) else TestOption(value.upper())
    except (AttributeError, ValueError) as error:
        raise ClimateRuleError("Opção inválida. Use A ou B.") from error


def calculate_service_temperature(tamb_c: NumericInput, delta_t_k: NumericInput) -> Decimal:
    """Calcula Ts somando a temperatura ambiente máxima ao maior delta T."""

    tamb = _decimal(tamb_c, field_name="Tamb")
    delta_t = _decimal(delta_t_k, field_name="Delta T")
    if delta_t < 0:
        raise ClimateRuleError("Delta T não pode ser negativo.")
    return tamb + delta_t


def available_options(
    epl: EPL | str, service_temperature_c: NumericInput
) -> tuple[TestOption, ...]:
    """Retorna somente as alternativas válidas para o EPL e Ts informados."""

    normalized_epl = _epl(epl)
    ts = _decimal(service_temperature_c, field_name="Ts")

    if normalized_epl.rule_group == 1:
        return (TestOption.A,) if ts <= Decimal("70") else (TestOption.A, TestOption.B)

    return (TestOption.A,) if ts <= Decimal("80") else (TestOption.A, TestOption.B)


def _chamber(temperature_c: Decimal, duration_hours: int) -> PhaseCondition:
    return PhaseCondition(
        temperature_c=temperature_c,
        duration_hours=duration_hours,
        humidity_percent=HUMIDITY_PERCENT,
        humidity_tolerance_percent=HUMIDITY_TOLERANCE_PERCENT,
    )


def _drying(temperature_c: Decimal) -> PhaseCondition:
    return PhaseCondition(temperature_c=temperature_c, duration_hours=336)


def _group_one_condition(epl: EPL, ts: Decimal, option: TestOption) -> ClimateCondition:
    if ts <= Decimal("70"):
        chamber_temperature = max(ts + Decimal("20"), Decimal("80"))
        return ClimateCondition(
            epl=epl,
            service_temperature_c=ts,
            option=option,
            chamber=_chamber(chamber_temperature, 672),
            drying=None,
            rule_id="G1-LOW-A",
        )

    drying_temperature = ts + Decimal("20")
    if ts < Decimal("75"):
        if option is TestOption.A:
            return ClimateCondition(
                epl=epl,
                service_temperature_c=ts,
                option=option,
                chamber=_chamber(drying_temperature, 672),
                drying=None,
                rule_id="G1-MID-A",
            )
        return ClimateCondition(
            epl=epl,
            service_temperature_c=ts,
            option=option,
            chamber=_chamber(Decimal("90"), 504),
            drying=_drying(drying_temperature),
            rule_id="G1-MID-B",
        )

    # Interpretação do laboratório: Ts = 75 °C pertence à faixa superior.
    if option is TestOption.A:
        return ClimateCondition(
            epl=epl,
            service_temperature_c=ts,
            option=option,
            chamber=_chamber(Decimal("95"), 336),
            drying=_drying(drying_temperature),
            rule_id="G1-HIGH-A",
        )
    return ClimateCondition(
        epl=epl,
        service_temperature_c=ts,
        option=option,
        chamber=_chamber(Decimal("90"), 504),
        drying=_drying(drying_temperature),
        rule_id="G1-HIGH-B",
    )


def _group_two_condition(epl: EPL, ts: Decimal, option: TestOption) -> ClimateCondition:
    drying_temperature = ts + Decimal("10")
    if ts <= Decimal("80"):
        return ClimateCondition(
            epl=epl,
            service_temperature_c=ts,
            option=option,
            chamber=_chamber(drying_temperature, 672),
            drying=None,
            rule_id="G2-LOW-A",
        )

    if ts <= Decimal("85"):
        if option is TestOption.A:
            return ClimateCondition(
                epl=epl,
                service_temperature_c=ts,
                option=option,
                chamber=_chamber(drying_temperature, 672),
                drying=None,
                rule_id="G2-MID-A",
            )
        return ClimateCondition(
            epl=epl,
            service_temperature_c=ts,
            option=option,
            chamber=_chamber(Decimal("90"), 336),
            drying=_drying(drying_temperature),
            rule_id="G2-MID-B",
        )

    if option is TestOption.A:
        return ClimateCondition(
            epl=epl,
            service_temperature_c=ts,
            option=option,
            chamber=_chamber(Decimal("95"), 336),
            drying=_drying(drying_temperature),
            rule_id="G2-HIGH-A",
        )
    return ClimateCondition(
        epl=epl,
        service_temperature_c=ts,
        option=option,
        chamber=_chamber(Decimal("90"), 504),
        drying=_drying(drying_temperature),
        rule_id="G2-HIGH-B",
    )


def resolve_condition(
    epl: EPL | str,
    service_temperature_c: NumericInput,
    option: TestOption | str,
) -> ClimateCondition:
    """Resolve a condição climática para uma Ts já calculada."""

    normalized_epl = _epl(epl)
    ts = _decimal(service_temperature_c, field_name="Ts")
    normalized_option = _option(option)

    if normalized_option not in available_options(normalized_epl, ts):
        raise ClimateRuleError(
            f"A opção {normalized_option.value} não está disponível para {normalized_epl.value} "
            f"com Ts = {ts} °C."
        )

    if normalized_epl.rule_group == 1:
        return _group_one_condition(normalized_epl, ts, normalized_option)
    return _group_two_condition(normalized_epl, ts, normalized_option)


def calculate_condition(
    epl: EPL | str,
    tamb_c: NumericInput,
    delta_t_k: NumericInput,
    option: TestOption | str,
) -> ClimateCondition:
    """Calcula Ts e retorna a condição normativa em uma única operação."""

    ts = calculate_service_temperature(tamb_c, delta_t_k)
    return resolve_condition(epl, ts, option)
