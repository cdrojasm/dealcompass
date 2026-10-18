from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from dealcompass_api.application.agent_runner import AgentRunner, DiscoverLeadsAgentUseCase
from dealcompass_api.application.create_search import CreateSearchUseCase
from dealcompass_api.domain.leads import Icp, Lead, LeadStage, Search
from dealcompass_api.infra.ai.llm_provider import FallbackHeuristicProvider
from dealcompass_api.infra.db.base import get_session
from dealcompass_api.infra.entrypoint import http
from dealcompass_api.infra.entrypoint.http import router


class FakeIcpRepo:
    def __init__(self) -> None:
        self.store: dict[UUID, Icp] = {}

    async def save(self, icp: Icp) -> Icp:
        self.store[icp.id] = icp
        return icp

    async def get(self, icp_id: UUID) -> Icp | None:
        return self.store.get(icp_id)

    async def list(self) -> list[Icp]:
        return list(self.store.values())

    async def delete(self, icp_id: UUID) -> bool:
        return self.store.pop(icp_id, None) is not None


class FakeSearchRepo:
    def __init__(self) -> None:
        self.store: dict[UUID, Search] = {}

    async def save(self, search: Search) -> Search:
        self.store[search.id] = search
        return search

    async def get(self, search_id: UUID) -> Search | None:
        return self.store.get(search_id)

    async def list(self, icp_id: UUID | None = None) -> list[Search]:
        items = list(self.store.values())
        if icp_id is not None:
            return [s for s in items if s.icp_id == icp_id]
        return items

    async def update_status(
        self,
        search_id: UUID,
        status: str,
        leads_found: int | None = None,
        contacted: int | None = None,
        rejected: int | None = None,
        fresh_leads: int | None = None,
    ) -> Search | None:
        search = self.store.get(search_id)
        if search is None:
            return None
        search.status = status
        if leads_found is not None:
            search.leads_found = leads_found
        if contacted is not None:
            search.contacted = contacted
        if rejected is not None:
            search.rejected = rejected
        if fresh_leads is not None:
            search.fresh_leads = fresh_leads
        return search


class FakeLeadRepo:
    def __init__(self) -> None:
        self.store: dict[UUID, Lead] = {}

    async def save(self, lead: Lead) -> Lead:
        self.store[lead.id] = lead
        return lead

    async def get(self, lead_id: UUID) -> Lead | None:
        return self.store.get(lead_id)

    async def list(
        self,
        search_id: UUID | None = None,
        stage: str | None = None,
    ) -> list[Lead]:
        items = list(self.store.values())
        if search_id is not None:
            items = [lead for lead in items if lead.search_id == search_id]
        if stage is not None:
            items = [lead for lead in items if lead.stage.value == stage]
        return items

    async def update_stage(self, lead_id: UUID, stage: str) -> Lead | None:
        lead = self.store.get(lead_id)
        if lead is None:
            return None
        lead.stage = LeadStage(stage)
        return lead


class FakeJobQueue:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, dict]] = []

    async def enqueue(self, kind: str, payload: dict) -> None:
        self.jobs.append((kind, payload))


def _build_client(monkeypatch) -> TestClient:
    icps = FakeIcpRepo()
    searches = FakeSearchRepo()
    leads = FakeLeadRepo()
    queue = FakeJobQueue()
    llm = FallbackHeuristicProvider()

    class StubFactory:
        @staticmethod
        def llm():
            return llm

        @staticmethod
        def agent(system_prompt: str | None = None) -> AgentRunner:
            if system_prompt:
                return AgentRunner(llm, system_prompt=system_prompt)
            return AgentRunner(llm)

        @staticmethod
        def discover_leads(_session) -> DiscoverLeadsAgentUseCase:
            return DiscoverLeadsAgentUseCase(llm=llm, searches=searches, leads=leads)

        @staticmethod
        def create_search(_session) -> CreateSearchUseCase:
            return CreateSearchUseCase(searches=searches, queue=queue, icps=icps)

        @staticmethod
        def icps(_session) -> FakeIcpRepo:
            return icps

        @staticmethod
        def searches(_session) -> FakeSearchRepo:
            return searches

        @staticmethod
        def leads(_session) -> FakeLeadRepo:
            return leads

    monkeypatch.setattr(http, "LeadsFactory", StubFactory)

    app = FastAPI()
    app.include_router(router)

    async def override_session() -> AsyncGenerator[None, None]:
        yield None

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def test_health_endpoints(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/health").json() == {"status": "ok"}


def test_icp_crud_endpoints(monkeypatch) -> None:
    client = _build_client(monkeypatch)

    resp = client.post(
        "/api/v1/icps",
        json={
            "name": "Growth Fintechs",
            "industry": "Fintech",
            "company_size": "50-200 employees",
            "target_roles": "VP Revenue",
        },
    )
    assert resp.status_code == 201
    icp = resp.json()
    icp_id = icp["id"]

    assert client.get(f"/api/v1/icps/{icp_id}").status_code == 200
    assert len(client.get("/api/v1/icps").json()) == 1

    assert client.delete(f"/api/v1/icps/{icp_id}").status_code == 204
    assert client.get(f"/api/v1/icps/{icp_id}").status_code == 404


def test_search_discover_and_lead_stage_endpoints(monkeypatch) -> None:
    client = _build_client(monkeypatch)

    # Creating search with non-existent ICP returns 404
    bad_search = client.post(
        "/api/v1/searches",
        json={"query": "SaaS", "location": "Colombia", "icp_id": str(uuid4())},
    )
    assert bad_search.status_code == 404

    icp_resp = client.post(
        "/api/v1/icps",
        json={"name": "LatAm SaaS", "industry": "B2B SaaS"},
    )
    icp_id = icp_resp.json()["id"]

    search_resp = client.post(
        "/api/v1/searches",
        json={"query": "LatAm SaaS", "location": "Colombia", "icp_id": icp_id},
    )
    assert search_resp.status_code == 201
    search_id = search_resp.json()["id"]

    discover_resp = client.post(f"/api/v1/searches/{search_id}/discover")
    assert discover_resp.status_code == 200
    assert discover_resp.json()["leads_saved"] == 2

    leads_resp = client.get(f"/api/v1/leads?search_id={search_id}")
    assert leads_resp.status_code == 200
    leads = leads_resp.json()
    assert len(leads) == 2

    lead_id = leads[0]["id"]
    patch_resp = client.patch(f"/api/v1/leads/{lead_id}", json={"stage": "qualification"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["stage"] == "qualification"

    updated_search = client.get(f"/api/v1/searches/{search_id}").json()
    assert updated_search["leads_found"] == 2
    assert updated_search["contacted"] == 1


def test_agent_run_endpoint_validation_and_not_found(monkeypatch) -> None:
    client = _build_client(monkeypatch)

    empty_resp = client.post("/api/v1/agent/run", json={"prompt": "   "})
    assert empty_resp.status_code == 422

    missing_search_resp = client.post(
        "/api/v1/agent/run",
        json={"search_id": str(uuid4())},
    )
    assert missing_search_resp.status_code == 404

    ok_resp = client.post(
        "/api/v1/agent/run",
        json={"prompt": "Suggest ICP criteria for B2B DevTools in Mexico"},
    )
    assert ok_resp.status_code == 200
    assert ok_resp.json()["steps"] == 1
