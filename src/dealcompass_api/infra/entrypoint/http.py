from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from dealcompass_api.application.create_search import CreateSearchCommand
from dealcompass_api.infra.db.base import get_session
from dealcompass_api.infra.factory.leads_factory import LeadsFactory

router = APIRouter()


class CreateSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=255)
    location: str = Field(min_length=1, max_length=255)


class SearchResponse(BaseModel):
    id: UUID
    query: str
    location: str
    status: str


class LeadResponse(BaseModel):
    id: UUID
    search_id: UUID
    company: str
    website: str | None
    stage: str


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/health")
async def api_health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/v1/searches", response_model=SearchResponse, status_code=201)
async def create_search(body: CreateSearchRequest, session: AsyncSession = Depends(get_session)):
    try:
        return await LeadsFactory.create_search(session).execute(
            CreateSearchCommand(query=body.query, location=body.location)
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
