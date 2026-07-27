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


class ConditionInputMode(StrEnum):
    """Origem dos dados usados para definir a condição do ensaio."""

    CALCULATED = "calculated"
    DIRECT_TS = "direct_ts"
    # Mantidos somente para abrir com segurança cadastros feitos durante o
    # desenvolvimento da v0.4.0. Novos cadastros usam DIRECT_CONFIGURATION.
    PLAN_CRITERION = "plan_criterion"
    DIRECT_CONFIGURATION = "direct_configuration"
    PLAN_DEFINED = "plan_defined"


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
    IN_TOLERANCE = "Em tolerância"
    OVERDUE = "Atrasado"


class EquipmentResource(StrEnum):
    """Recursos físicos que podem ficar indisponíveis para todos os ensaios."""

    CLIMATE_CHAMBER = "climate_chamber"
    DRYING = "drying"

    @property
    def label(self) -> str:
        """Nome curto apresentado ao operador."""

        if self is EquipmentResource.CLIMATE_CHAMBER:
            return "Câmara climática"
        return "Secagem"
