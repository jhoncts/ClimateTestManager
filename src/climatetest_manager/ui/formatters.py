"""Formatação e normalização de valores apresentados pela interface."""

from decimal import Decimal


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
