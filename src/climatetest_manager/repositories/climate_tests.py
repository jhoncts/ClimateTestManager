"""Persistência dos ensaios climáticos com SQLAlchemy."""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, sessionmaker

from climatetest_manager.database.models import ClimateTestRecord
from climatetest_manager.domain.enums import TestSituation


@dataclass(frozen=True, slots=True)
class RecentClimateTest:
    """Dados mínimos de um ensaio recente apresentados no dashboard."""

    id: int
    client: str
    process_number: str
    product: str
    epl: str
    service_temperature_c: str
    selected_option: str
    situation: str


class ClimateTestRepository:
    """Isola o restante da aplicação dos detalhes de sessão do banco."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, climate_test: ClimateTestRecord) -> int:
        """Persiste um ensaio completo em uma única transação."""

        with self._session_factory() as session:
            session.add(climate_test)
            session.commit()
            return climate_test.id

    def count_by_situations(self, *situations: TestSituation) -> int:
        """Conta ensaios que estejam em qualquer uma das situações recebidas."""

        values = [situation.value for situation in situations]
        with self._session_factory() as session:
            statement = select(func.count(ClimateTestRecord.id)).where(
                ClimateTestRecord.situation.in_(values)
            )
            return session.scalar(statement) or 0

    def list_recent(self, *, limit: int = 6) -> list[RecentClimateTest]:
        """Retorna os cadastros mais recentes sem expor objetos de sessão à UI."""

        with self._session_factory() as session:
            statement = (
                select(ClimateTestRecord)
                .options(joinedload(ClimateTestRecord.condition_snapshot))
                .order_by(ClimateTestRecord.created_at.desc(), ClimateTestRecord.id.desc())
                .limit(limit)
            )
            records = session.scalars(statement).all()

            return [
                RecentClimateTest(
                    id=record.id,
                    client=record.client,
                    process_number=record.process_number,
                    product=record.product,
                    epl=record.epl,
                    service_temperature_c=str(record.service_temperature_c),
                    selected_option=record.selected_option or "-",
                    situation=record.situation,
                )
                for record in records
            ]
