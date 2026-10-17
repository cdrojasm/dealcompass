from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dealcompass_api.domain.leads import Lead, LeadStage, Search
from dealcompass_api.infra.db.models import JobModel, LeadModel, SearchModel


class SqlAlchemySearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, search: Search) -> Search:
        model = SearchModel(id=search.id, query=search.query, location=search.location, status=search.status)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def get(self, search_id: UUID) -> Search | None:
        model = await self._session.get(SearchModel, search_id)
        return self._to_domain(model) if model else None

    async def list(self) -> list[Search]:
        rows = await self._session.scalars(select(SearchModel).order_by(SearchModel.created_at.desc()))
        return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(model: SearchModel) -> Search:
        return Search(
            id=model.id,
            query=model.query,
            location=model.location,
            status=model.status,
            created_at=model.created_at,
        )


class SqlAlchemyLeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, search_id: UUID | None = None) -> list[Lead]:
        stmt = select(LeadModel).order_by(LeadModel.created_at.desc())
        if search_id:
            stmt = stmt.where(LeadModel.search_id == search_id)
        rows = await self._session.scalars(stmt)
        return [
            Lead(
                id=row.id,
                search_id=row.search_id,
                company=row.company,
                website=row.website,
                stage=LeadStage(row.stage),
                created_at=row.created_at,
            )
            for row in rows
        ]


class SqlAlchemyJobQueue:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(self, kind: str, payload: dict) -> None:
        self._session.add(JobModel(kind=kind, payload=payload))
        await self._session.commit()
