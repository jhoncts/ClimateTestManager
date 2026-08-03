"""Exportações locais sem dependência de Excel, Outlook ou serviços pagos."""

import csv
import hashlib
import io
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from climatetest_manager.config import get_exports_directory, get_external_backup_directory
from climatetest_manager.domain.enums import ConditionInputMode
from climatetest_manager.services.climate_tests import ClimateTestDetails, ClimateTestListItem


@dataclass(frozen=True, slots=True)
class DatabaseVerification:
    """Evidência de integridade produzida para uma cópia SQLite fechada."""

    file_name: str
    sha256: str
    size_bytes: int
    schema_version: int
    quick_check: str
    foreign_key_violations: int
    verified_at: str


def _escape_ics(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _csv_cell(value: str) -> str:
    """Neutraliza conteúdo que planilhas poderiam interpretar como fórmula."""

    return f"'{value}" if value.startswith(("=", "+", "-", "@")) else value


def export_tests_csv(
    tests: list[ClimateTestListItem],
    *,
    output_directory: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    """Exporta uma fotografia dos ensaios para consulta e auditoria."""

    if output_path is None:
        directory = output_directory or get_exports_directory()
        directory.mkdir(parents=True, exist_ok=True)
        output_path = directory / f"ensaios_{datetime.now():%Y%m%d_%H%M%S}.csv"
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(build_tests_csv_bytes(tests))
    return output_path


def build_tests_csv_bytes(tests: list[ClimateTestListItem]) -> bytes:
    """Monta o CSV em memória para permitir que o usuário escolha onde salvá-lo."""

    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=";")
    writer.writerow(
        [
            "ID",
            "Cliente",
            "Processo",
            "Produto",
            "Quantidade de amostras",
            "Origem da condição",
            "EPL",
            "Ts (°C)",
            "Critério ou referência",
            "Opção",
            "Câmara (°C)",
            "Umidade (% UR)",
            "Permanência na câmara (h)",
            "Secagem necessária",
            "Secagem (°C)",
            "Permanência na secagem (h)",
            "Situação",
            "Pausado",
            "Motivo da pausa",
            "Progresso da etapa (%)",
            "Condição",
            "Retirada recomendada",
            "Último prazo permitido",
        ]
    )
    for item in tests:
        exact_ts = item.input_mode in {
            ConditionInputMode.CALCULATED.value,
            ConditionInputMode.DIRECT_TS.value,
        }
        source = {
            ConditionInputMode.CALCULATED.value: "Calculada por Tamb + Delta T",
            ConditionInputMode.DIRECT_TS.value: "Ts informado",
            ConditionInputMode.PLAN_CRITERION.value: "Personalizado",
            ConditionInputMode.DIRECT_CONFIGURATION.value: "Personalizado",
            ConditionInputMode.PLAN_DEFINED.value: "Personalizado",
        }.get(item.input_mode, "Origem não identificada")
        writer.writerow(
            [
                item.id,
                _csv_cell(item.client),
                _csv_cell(item.process_number),
                _csv_cell(item.product),
                item.sample_quantity,
                source,
                item.epl,
                (str(item.service_temperature_c).replace(".", ",") if exact_ts else ""),
                _csv_cell(item.ts_reference or ""),
                "" if item.selected_option == "-" else item.selected_option,
                str(item.chamber_temperature_c).replace(".", ","),
                str(item.chamber_humidity_percent).replace(".", ","),
                item.chamber_duration_hours,
                "Sim" if item.drying_required else "Não",
                (
                    str(item.drying_temperature_c).replace(".", ",")
                    if item.drying_temperature_c is not None
                    else ""
                ),
                item.drying_duration_hours or "",
                item.situation,
                "Sim" if item.is_paused else "Não",
                _csv_cell(item.pause_reason or ""),
                f"{item.progress_percent * 100:.0f}",
                item.deadline_condition or "",
                item.nominal_end_at.strftime("%d/%m/%Y %H:%M") if item.nominal_end_at else "",
                item.maximum_end_at.strftime("%d/%m/%Y %H:%M") if item.maximum_end_at else "",
            ]
        )
    return ("\ufeff" + stream.getvalue()).encode("utf-8")


def build_database_backup_bytes(database_path: Path) -> bytes:
    """Cria uma cópia consistente do SQLite aberto usando a API de backup."""

    if not database_path.exists():
        raise ValueError("O banco de dados ativo não foi encontrado.")
    with TemporaryDirectory() as temporary_directory:
        backup_path = Path(temporary_directory) / "climatetest_manager_backup.db"
        source = sqlite3.connect(database_path)
        destination = sqlite3.connect(backup_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()
        return backup_path.read_bytes()


def verify_sqlite_database(
    database_path: Path,
    *,
    verified_at: datetime | None = None,
) -> DatabaseVerification:
    """Confirma formato, integridade, vínculos e resumo criptográfico da cópia."""

    if not database_path.exists():
        raise ValueError("O arquivo SQLite a verificar não foi encontrado.")
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True)
        quick_check_row = connection.execute("PRAGMA quick_check").fetchone()
        quick_check = str(quick_check_row[0]) if quick_check_row else "sem resultado"
        if quick_check.casefold() != "ok":
            raise ValueError(f"A verificação de integridade falhou: {quick_check}")
        foreign_key_violations = len(connection.execute("PRAGMA foreign_key_check").fetchall())
        if foreign_key_violations:
            raise ValueError(
                "A verificação encontrou "
                f"{foreign_key_violations} violação(ões) de integridade referencial."
            )
        schema_row = connection.execute("PRAGMA user_version").fetchone()
        schema_version = int(schema_row[0]) if schema_row else 0
    except sqlite3.DatabaseError as error:
        raise ValueError(f"A cópia SQLite não pôde ser validada: {error}") from error
    finally:
        if connection is not None:
            connection.close()

    content = database_path.read_bytes()
    effective_time = verified_at or datetime.now(UTC)
    if effective_time.tzinfo is None:
        effective_time = effective_time.replace(tzinfo=UTC)
    return DatabaseVerification(
        file_name=database_path.name,
        sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        schema_version=schema_version,
        quick_check=quick_check,
        foreign_key_violations=foreign_key_violations,
        verified_at=effective_time.astimezone(UTC).isoformat(),
    )


def _write_backup_manifest(
    backup_path: Path,
    verification: DatabaseVerification,
) -> Path:
    """Grava a evidência ao lado do backup por substituição atômica."""

    manifest_path = backup_path.with_suffix(backup_path.suffix + ".manifest.json")
    temporary = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(asdict(verification), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(manifest_path)
    return manifest_path


def create_daily_database_backup(
    database_path: Path,
    *,
    backup_directory: Path | None = None,
    now: datetime | None = None,
    retention_count: int = 30,
) -> Path:
    """Cria no máximo um backup local por dia e mantém as cópias mais recentes."""

    if retention_count < 1:
        raise ValueError("A retenção precisa manter pelo menos uma cópia.")
    effective_now = now or datetime.now()
    destination_directory = backup_directory or database_path.parent / "backups"
    destination_directory.mkdir(parents=True, exist_ok=True)
    destination = destination_directory / f"climatetest_auto_{effective_now:%Y%m%d}.db"
    if not destination.exists():
        temporary = destination.with_suffix(".tmp")
        temporary.write_bytes(build_database_backup_bytes(database_path))
        temporary.replace(destination)
    try:
        verification = verify_sqlite_database(destination, verified_at=effective_now)
    except ValueError:
        temporary = destination.with_suffix(".tmp")
        temporary.write_bytes(build_database_backup_bytes(database_path))
        temporary.replace(destination)
        verification = verify_sqlite_database(destination, verified_at=effective_now)
    _write_backup_manifest(destination, verification)
    backups = sorted(
        destination_directory.glob("climatetest_auto_*.db"),
        key=lambda path: path.name,
        reverse=True,
    )
    for expired in backups[retention_count:]:
        expired.unlink()
        expired.with_suffix(expired.suffix + ".manifest.json").unlink(missing_ok=True)
    return destination


def create_configured_database_backups(
    database_path: Path,
    *,
    now: datetime | None = None,
) -> tuple[Path, ...]:
    """Mantém uma cópia local e, quando configurada, outra na pasta externa."""

    local_directory = database_path.parent / "backups"
    directories = [local_directory]
    external_directory = get_external_backup_directory()
    if external_directory is not None and external_directory.resolve() != local_directory.resolve():
        directories.append(external_directory)
    return tuple(
        create_daily_database_backup(
            database_path,
            backup_directory=directory,
            now=now,
        )
        for directory in directories
    )


def export_test_calendar(
    details: ClimateTestDetails,
    *,
    output_directory: Path | None = None,
) -> Path:
    """Gera um arquivo ICS importável por Outlook, Google Agenda e outros calendários."""

    events: list[tuple[str, datetime, str]] = []
    if details.chamber_nominal_end_at:
        events.append(
            (
                "Retirar amostra da câmara",
                details.chamber_nominal_end_at,
                f"Limite máximo: {details.chamber_maximum_end_at:%d/%m/%Y %H:%M}",
            )
        )
    if details.drying_nominal_end_at:
        events.append(
            (
                "Retirar amostra da secagem",
                details.drying_nominal_end_at,
                f"Limite máximo: {details.drying_maximum_end_at:%d/%m/%Y %H:%M}",
            )
        )
    if not events:
        raise ValueError("O ensaio ainda não possui um prazo para adicionar à agenda.")

    directory = output_directory or get_exports_directory()
    directory.mkdir(parents=True, exist_ok=True)
    safe_process = "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in details.process_number
    )
    path = directory / f"ensaio_{details.id}_{safe_process}.ics"
    generated_at = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ClimateTest Manager//PT-BR"]
    for index, (title, starts_at, description) in enumerate(events, start=1):
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:climatetest-{details.id}-{index}@local",
                f"DTSTAMP:{generated_at}",
                f"DTSTART:{starts_at:%Y%m%dT%H%M%S}",
                f"DTEND:{(starts_at.replace(microsecond=0) + timedelta(minutes=30)):%Y%m%dT%H%M%S}",
                f"SUMMARY:{_escape_ics(title)} — processo {_escape_ics(details.process_number)}",
                f"DESCRIPTION:{_escape_ics(description)}",
                "BEGIN:VALARM",
                "TRIGGER:-PT2H",
                "ACTION:DISPLAY",
                "DESCRIPTION:Prazo do ensaio climático",
                "END:VALARM",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return path
