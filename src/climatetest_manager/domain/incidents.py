"""Catálogo controlado de falhas e prioridade atribuída automaticamente."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IncidentReason:
    code: str
    label: str
    severity: str
    guidance: str


INCIDENT_REASONS: tuple[IncidentReason, ...] = (
    IncidentReason(
        "data_integrity",
        "Dados ausentes, divergentes ou possivelmente corrompidos",
        "Crítica",
        "Interrompa a alteração dos registros e preserve as evidências.",
    ),
    IncidentReason(
        "database_backup",
        "Banco de dados, backup ou restauração",
        "Crítica",
        "Evite substituir arquivos e informe qual cópia foi preservada.",
    ),
    IncidentReason(
        "software_crash",
        "Aplicativo não abre ou fechou inesperadamente",
        "Alta",
        "Anote a tela, o horário e a última operação realizada.",
    ),
    IncidentReason(
        "access_permissions",
        "Login, conta ou permissão incorreta",
        "Alta",
        "Não compartilhe senhas; registre qual acesso foi impedido.",
    ),
    IncidentReason(
        "notifications",
        "Aviso, notificação do Windows ou e-mail não enviado",
        "Média",
        "Confira manualmente os próximos prazos até a avaliação do administrador.",
    ),
    IncidentReason(
        "performance",
        "Lentidão, congelamento ou demora excessiva",
        "Média",
        "Registre em qual tela ocorreu e se o sistema voltou a responder.",
    ),
    IncidentReason(
        "interface",
        "Erro visual, informação cortada ou dificuldade de uso",
        "Baixa",
        "Se possível, preserve uma captura da tela.",
    ),
    IncidentReason(
        "other",
        "Outros",
        "Média",
        "Descreva o tipo de falha com clareza no campo abaixo.",
    ),
)

INCIDENT_REASON_BY_CODE = {reason.code: reason for reason in INCIDENT_REASONS}


def incident_reason(code: str) -> IncidentReason:
    try:
        return INCIDENT_REASON_BY_CODE[code]
    except KeyError as error:
        raise ValueError("Motivo de falha inválido.") from error
