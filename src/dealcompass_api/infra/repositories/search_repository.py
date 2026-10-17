from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dealcompass_api.domain.leads import Icp, Lead, LeadStage, Search
from dealcompass_api.infra.db.models import IcpModel, JobModel, LeadModel, SearchModel


class SqlAlchemyIcpRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, icp: Icp) -> Icp:
        model = IcpModel(
            id=icp.id,
            name=icp.name,
            industry=icp.industry,
            company_size=icp.company_size,
            target_roles=icp.target_roles,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def get(self, icp_id: UUID) -> Icp | None:
        model = await self._session.get(IcpModel, icp_id)
        return self._to_domain(model) if model else None

    async def list(self) -> list[Icp]:
        rows = await self._session.scalars(select(IcpModel).order_by(IcpModel.created_at.desc()))
        return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(model: IcpModel) -> Icp:
        return Icp(
            id=model.id,
            name=model.name,
            industry=model.industry,
            company_size=model.company_size,
            target_roles=model.target_roles,
            created_at=model.created_at,
        )


class SqlAlchemySearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, search: Search) -> Search:
        model = SearchModel(
            id=search.id,
            icp_id=search.icp_id,
            query=search.query,
            location=search.location,
            status=search.status,
            leads_found=search.leads_found,
            contacted=search.contacted,
            rejected=search.rejected,
            fresh_leads=search.fresh_leads,
        )
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
            icp_id=model.icp_id,
            query=model.query,
            location=model.location,
            status=model.status,
            leads_found=model.leads_found,
            contacted=model.contacted,
            rejected=model.rejected,
            fresh_leads=model.fresh_leads,
            created_at=model.created_at,
            updated_at=model.updated_at,
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
                icp_id=row.icp_id,
                name=row.name,
                role=row.role,
                company=row.company,
                website=row.website,
                industry=row.industry,
                company_size=row.company_size,
                location=row.location,
                score=row.score,
                stage=LeadStage(row.stage),
                email=row.email,
                linkedin=row.linkedin,
                last_activity_at=row.last_activity_at,
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
