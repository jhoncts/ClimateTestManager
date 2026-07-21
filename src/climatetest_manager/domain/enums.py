"""Vocabulário controlado utilizado pelo domínio."""

from enum import StrEnum


class EPL(StrEnum):
    """Níveis de proteção de equipamento tratados pela Tabela 17."""

    GA = "Ga"
    GB = "Gb"
    GC = "Gc"
    DA = "Da"
    DB = "Db"
    DC = "Dc"
    MA = "Ma"
    MB = "Mb"

    @property
    def rule_group(self) -> int:
        """Agrupa EPLs que compartilham as mesmas faixas normativas."""

        return 2 if self in {EPL.GC, EPL.DC} else 1


class TestOption(StrEnum):
    """Alternativa de condição permitida pela Tabela 17."""

    A = "A"
    B = "B"


class TestSituation(StrEnum):
    """Etapa operacional atual do ensaio."""

    WAITING = "Aguardando"
    IN_CHAMBER = "Na Câmara"
    DRYING = "Em Secagem"
    FINISHED = "Finalizado"
    CANCELLED = "Cancelado"


class DeadlineCondition(StrEnum):
    """Condição de prazo da próxima ação do ensaio."""

    ON_TIME = "No prazo"
    DUE_TODAY = "Vence hoje"
    OVERDUE = "Atrasado"
