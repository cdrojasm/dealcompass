from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from dealcompass_api.application.create_search import CreateSearchCommand
from dealcompass_api.domain.leads import Icp, Lead, LeadStage, NotFoundError
from dealcompass_api.infra.db.base import get_session
from dealcompass_api.infra.factory.leads_factory import LeadsFactory

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]


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


class CreateLeadRequest(BaseModel):
    search_id: UUID
    icp_id: UUID | None = None
    name: str = Field(default="", max_length=255)
    role: str = Field(default="", max_length=255)
    company: str = Field(min_length=1, max_length=255)
    website: str | None = Field(default=None, max_length=512)
    industry: str = Field(default="", max_length=255)
    company_size: str = Field(default="", max_length=255)
    location: str = Field(default="", max_length=255)
    score: int = Field(default=85, ge=0, le=100)
    stage: LeadStage = LeadStage.DISCOVERED
    email: str | None = Field(default=None, max_length=255)
    linkedin: str | None = Field(default=None, max_length=512)


class UpdateLeadStageRequest(BaseModel):
    stage: LeadStage


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


class AgentRunRequest(BaseModel):
    prompt: str = Field(default="", max_length=4000)
    system_prompt: str | None = Field(default=None, max_length=4000)
    search_id: UUID | None = None


class AgentRunResponse(BaseModel):
    output: str
    steps: int
    provider: str
    model: str
    leads_saved: int = 0


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/health")
async def api_health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/v1/agent/run", response_model=AgentRunResponse)
async def run_agent(body: AgentRunRequest, session: SessionDep):
    try:
        if body.search_id is not None:
            result, saved_leads = await LeadsFactory.discover_leads(session).execute(body.search_id)
            return AgentRunResponse(
                output=result.output,
                steps=result.steps,
                provider=result.provider,
                model=result.model,
                leads_saved=len(saved_leads),
            )
        if not body.prompt.strip():
            raise ValueError("Agent prompt cannot be empty when search_id is not provided")
        result = await LeadsFactory.agent(body.system_prompt).run(body.prompt)
        return AgentRunResponse(
            output=result.output,
            steps=result.steps,
            provider=result.provider,
            model=result.model,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/v1/icps", response_model=IcpResponse, status_code=201)
async def create_icp(body: CreateIcpRequest, session: SessionDep):
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
async def list_icps(session: SessionDep):
    return await LeadsFactory.icps(session).list()


@router.get("/api/v1/icps/{icp_id}", response_model=IcpResponse)
async def get_icp(icp_id: UUID, session: SessionDep):
    icp = await LeadsFactory.icps(session).get(icp_id)
    if icp is None:
        raise HTTPException(status_code=404, detail="ICP not found")
    return icp


@router.delete("/api/v1/icps/{icp_id}", status_code=204)
async def delete_icp(icp_id: UUID, session: SessionDep) -> Response:
    deleted = await LeadsFactory.icps(session).delete(icp_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="ICP not found")
    return Response(status_code=204)


@router.post("/api/v1/searches", response_model=SearchResponse, status_code=201)
async def create_search(body: CreateSearchRequest, session: SessionDep):
    try:
        return await LeadsFactory.create_search(session).execute(
            CreateSearchCommand(query=body.query, location=body.location, icp_id=body.icp_id)
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/v1/searches", response_model=list[SearchResponse])
async def list_searches(session: SessionDep, icp_id: UUID | None = None):
    return await LeadsFactory.searches(session).list(icp_id=icp_id)


@router.get("/api/v1/searches/{search_id}", response_model=SearchResponse)
async def get_search(search_id: UUID, session: SessionDep):
    search = await LeadsFactory.searches(session).get(search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="Search not found")
    return search


@router.post("/api/v1/searches/{search_id}/discover", response_model=AgentRunResponse)
async def discover_search_leads(search_id: UUID, session: SessionDep):
    try:
        result, saved_leads = await LeadsFactory.discover_leads(session).execute(search_id)
        return AgentRunResponse(
            output=result.output,
            steps=result.steps,
            provider=result.provider,
            model=result.model,
            leads_saved=len(saved_leads),
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/v1/leads", response_model=list[LeadResponse])
async def list_leads(
    session: SessionDep,
    search_id: UUID | None = None,
    stage: LeadStage | None = None,
):
    return await LeadsFactory.leads(session).list(
        search_id=search_id,
        stage=stage.value if stage else None,
    )


@router.get("/api/v1/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: UUID, session: SessionDep):
    lead = await LeadsFactory.leads(session).get(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/api/v1/leads", response_model=LeadResponse, status_code=201)
async def create_lead(body: CreateLeadRequest, session: SessionDep):
    search = await LeadsFactory.searches(session).get(body.search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="Search not found")
    try:
        lead = await LeadsFactory.leads(session).save(
            Lead(
                search_id=body.search_id,
                icp_id=body.icp_id or search.icp_id,
                name=body.name,
                role=body.role,
                company=body.company,
                website=body.website,
                industry=body.industry,
                company_size=body.company_size,
                location=body.location or search.location,
                score=body.score,
                stage=body.stage,
                email=body.email,
                linkedin=body.linkedin,
            )
        )
        all_leads = await LeadsFactory.leads(session).list(search_id=search.id)
        await LeadsFactory.searches(session).update_status(
            search.id,
            status=search.status,
            leads_found=len(all_leads),
            contacted=sum(
                1
                for item in all_leads
                if item.stage in (LeadStage.CONTACTED, LeadStage.QUALIFICATION)
            ),
            rejected=sum(1 for item in all_leads if item.stage == LeadStage.DISCARDED),
            fresh_leads=sum(1 for item in all_leads if item.stage == LeadStage.DISCOVERED),
        )
        return lead
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/api/v1/leads/{lead_id}", response_model=LeadResponse)
async def update_lead_stage(
    lead_id: UUID,
    body: UpdateLeadStageRequest,
    session: SessionDep,
):
    lead = await LeadsFactory.leads(session).update_stage(lead_id, body.stage.value)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    search = await LeadsFactory.searches(session).get(lead.search_id)
    if search is not None:
        all_leads = await LeadsFactory.leads(session).list(search_id=search.id)
        await LeadsFactory.searches(session).update_status(
            search.id,
            status=search.status,
            leads_found=len(all_leads),
            contacted=sum(
                1
                for item in all_leads
                if item.stage in (LeadStage.CONTACTED, LeadStage.QUALIFICATION)
            ),
            rejected=sum(1 for item in all_leads if item.stage == LeadStage.DISCARDED),
            fresh_leads=sum(1 for item in all_leads if item.stage == LeadStage.DISCOVERED),
        )
    return lead
