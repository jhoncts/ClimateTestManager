"""Formatação e normalização de valores apresentados pela interface."""

from datetime import datetime
from decimal import Decimal

from climatetest_manager.domain.enums import ConditionInputMode


def format_decimal(value: Decimal | str) -> str:
    """Formata um decimal sem zeros supérfluos usando vírgula na interface."""

    decimal_value = value if isinstance(value, Decimal) else Decimal(value)
    formatted = format(decimal_value, "f")
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return (formatted or "0").replace(".", ",")


def normalize_decimal_input(value: str, *, allow_negative: bool = False) -> str:
    """Mantém somente um número decimal e converte ponto para vírgula."""

    normalized = value.replace(".", ",")
    is_negative = allow_negative and normalized.startswith("-")
    digits: list[str] = []
    separator_found = False

    for character in normalized:
        if character.isdecimal():
            digits.append(character)
        elif character == "," and not separator_found:
            digits.append(character)
            separator_found = True

    result = "".join(digits)
    return f"-{result}" if is_negative else result


def normalize_date_input(value: str) -> str:
    """Mantém até oito dígitos e insere as barras de DD/MM/AAAA."""

    digits = "".join(character for character in value if character.isdecimal())[:8]
    if len(digits) <= 2:
        return digits
    if len(digits) <= 4:
        return f"{digits[:2]}/{digits[2:]}"
    return f"{digits[:2]}/{digits[2:4]}/{digits[4:]}"


def normalize_time_input(value: str) -> str:
    """Mantém até quatro dígitos e insere os dois-pontos de HH:MM."""

    digits = "".join(character for character in value if character.isdecimal())[:4]
    if len(digits) <= 2:
        return digits
    return f"{digits[:2]}:{digits[2:]}"


def format_hours_as_days(hours: int) -> str:
    """Representa uma quantidade de horas como dias e horas."""

    if hours < 0:
        raise ValueError("A duração não pode ser negativa.")

    days, remaining_hours = divmod(hours, 24)
    parts: list[str] = []
    if days:
        parts.append(f"{days} {'dia' if days == 1 else 'dias'}")
    if remaining_hours or not parts:
        parts.append(f"{remaining_hours} {'hora' if remaining_hours == 1 else 'horas'}")
    return " e ".join(parts)


def format_duration_detail(duration_hours: int, positive_tolerance_hours: int) -> str:
    """Exibe a duração nominal e o limite superior em linguagem operacional."""

    nominal = format_hours_as_days(duration_hours)
    maximum = format_hours_as_days(duration_hours + positive_tolerance_hours)
    return f"{nominal} nominais • limite: {maximum}"


def format_datetime(value: datetime | None) -> str:
    """Apresenta horário operacional no padrão brasileiro."""

    return value.strftime("%d/%m/%Y %H:%M") if value else "—"


def parse_local_datetime(date_text: str, time_text: str) -> datetime:
    """Converte data e hora informadas manualmente em um instante local."""

    try:
        return datetime.strptime(f"{date_text.strip()} {time_text.strip()}", "%d/%m/%Y %H:%M")
    except ValueError as error:
        raise ValueError("Informe data e hora nos formatos DD/MM/AAAA e HH:MM.") from error


def format_condition_source(input_mode: str) -> str:
    """Traduz a origem persistida para uma descrição curta e clara."""

    labels = {
        ConditionInputMode.CALCULATED.value: "Calculada por Tamb + ΔT",
        ConditionInputMode.DIRECT_TS.value: "Ts informado",
        ConditionInputMode.PLAN_CRITERION.value: "Personalizado",
        ConditionInputMode.DIRECT_CONFIGURATION.value: "Personalizado",
        ConditionInputMode.PLAN_DEFINED.value: "Personalizado",
    }
    return labels.get(input_mode, "Origem não identificada")


def format_thermal_summary(
    *,
    input_mode: str,
    epl: str,
    service_temperature_c: Decimal | str,
    ts_reference: str | None,
    selected_option: str,
) -> str:
    """Evita exibir valores térmicos fictícios nos modos simplificados."""

    epl_text = f"EPL {epl}" if epl else "EPL não informado"
    if input_mode in {
        ConditionInputMode.CALCULATED.value,
        ConditionInputMode.DIRECT_TS.value,
    }:
        option = f" • Opção {selected_option}" if selected_option and selected_option != "-" else ""
        return f"{epl_text} • Ts {format_decimal(service_temperature_c)} °C{option}"
    return f"{epl_text} • Condição personalizada" if epl else "Condição personalizada"
