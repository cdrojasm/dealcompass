from sqlalchemy.ext.asyncio import AsyncSession

from dealcompass_api.application.create_search import CreateSearchUseCase
from dealcompass_api.infra.repositories.search_repository import (
    SqlAlchemyIcpRepository,
    SqlAlchemyJobQueue,
    SqlAlchemyLeadRepository,
    SqlAlchemySearchRepository,
)


class LeadsFactory:
    """Composition root for the lead-generation use cases."""

    @staticmethod
    def create_search(session: AsyncSession) -> CreateSearchUseCase:
        return CreateSearchUseCase(SqlAlchemySearchRepository(session), SqlAlchemyJobQueue(session))

    @staticmethod
    def icps(session: AsyncSession) -> SqlAlchemyIcpRepository:
        return SqlAlchemyIcpRepository(session)

    @staticmethod
    def searches(session: AsyncSession) -> SqlAlchemySearchRepository:
        return SqlAlchemySearchRepository(session)

    @staticmethod
    def leads(session: AsyncSession) -> SqlAlchemyLeadRepository:
        return SqlAlchemyLeadRepository(session)
