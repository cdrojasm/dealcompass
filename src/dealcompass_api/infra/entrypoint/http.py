from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from dealcompass_api.application.create_search import CreateSearchCommand
from dealcompass_api.domain.leads import Icp
from dealcompass_api.infra.db.base import get_session
from dealcompass_api.infra.factory.leads_factory import LeadsFactory

router = APIRouter()


class CreateIcpRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    industry: str = Field(default="", max_length=255)
    company_size: str = Field(default="", max_length=255)
    target_roles: str = Field(default="", max_length=255)


class IcpResponse(BaseModel):
    id: UUID
    name: str
    industry: str
    company_size: str
    target_roles: str


class CreateSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=255)
    location: str = Field(min_length=1, max_length=255)
    icp_id: UUID | None = None


class SearchResponse(BaseModel):
    id: UUID
    icp_id: UUID | None = None
    query: str
    location: str
    status: str
    leads_found: int = 0
    contacted: int = 0
    rejected: int = 0
    fresh_leads: int = 0


class LeadResponse(BaseModel):
    id: UUID
    search_id: UUID
    icp_id: UUID | None = None
    name: str = ""
    role: str = ""
    company: str
    website: str | None = None
    industry: str = ""
    company_size: str = ""
    location: str = ""
    score: int = 0
    stage: str
    email: str | None = None
    linkedin: str | None = None


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/health")
async def api_health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/v1/icps", response_model=IcpResponse, status_code=201)
async def create_icp(body: CreateIcpRequest, session: AsyncSession = Depends(get_session)):
    try:
        return await LeadsFactory.icps(session).save(
            Icp(
                name=body.name,
                industry=body.industry,
                company_size=body.company_size,
                target_roles=body.target_roles,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/v1/icps", response_model=list[IcpResponse])
async def list_icps(session: AsyncSession = Depends(get_session)):
    return await LeadsFactory.icps(session).list()


@router.post("/api/v1/searches", response_model=SearchResponse, status_code=201)
async def create_search(body: CreateSearchRequest, session: AsyncSession = Depends(get_session)):
    try:
        return await LeadsFactory.create_search(session).execute(
            CreateSearchCommand(query=body.query, location=body.location, icp_id=body.icp_id)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/v1/searches", response_model=list[SearchResponse])
async def list_searches(session: AsyncSession = Depends(get_session)):
    return await LeadsFactory.searches(session).list()


@router.get("/api/v1/searches/{search_id}", response_model=SearchResponse)
async def get_search(search_id: UUID, session: AsyncSession = Depends(get_session)):
    search = await LeadsFactory.searches(session).get(search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="Search not found")
    return search


@router.get("/api/v1/leads", response_model=list[LeadResponse])
async def list_leads(search_id: UUID | None = None, session: AsyncSession = Depends(get_session)):
    return await LeadsFactory.leads(session).list(search_id)
