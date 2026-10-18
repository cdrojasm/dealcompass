import asyncio
from uuid import UUID, uuid4

import pytest

from dealcompass_api.application.agent_runner import AgentRunner, DiscoverLeadsAgentUseCase
from dealcompass_api.config import Settings
from dealcompass_api.domain.agent import Message, Role, ToolCall, ToolDefinition
from dealcompass_api.domain.leads import Lead, LeadStage, NotFoundError, Search
from dealcompass_api.infra.ai.llm_provider import (
    FallbackHeuristicProvider,
    OpenAICompatibleProvider,
    create_llm_provider,
)


class FakeLLMProvider:
    def __init__(self) -> None:
        self.provider_name = "custom-provider"
        self.model_name = "test-model"
        self.calls = 0

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.2,
    ) -> Message:
        self.calls += 1
        if self.calls == 1 and tools:
            return Message(
                role=Role.ASSISTANT,
                content="Calling tool",
                tool_calls=[
                    ToolCall(
                        id="tc_1",
                        name=tools[0].name,
                        arguments={"company": "Acme Cloud"},
                    )
                ],
            )
        return Message(role=Role.ASSISTANT, content="Done")


class InMemorySearchRepo:
    def __init__(self, search: Search) -> None:
        self.store = {search.id: search}

    async def save(self, search: Search) -> Search:
        self.store[search.id] = search
        return search

    async def get(self, search_id: UUID) -> Search | None:
        return self.store.get(search_id)

    async def list(self, icp_id: UUID | None = None) -> list[Search]:
        values = list(self.store.values())
        if icp_id is not None:
            return [s for s in values if s.icp_id == icp_id]
        return values

    async def update_status(
        self,
        search_id: UUID,
        status: str,
        leads_found: int | None = None,
        contacted: int | None = None,
        rejected: int | None = None,
        fresh_leads: int | None = None,
    ) -> Search | None:
        s = self.store.get(search_id)
        if not s:
            return None
        s.status = status
        if leads_found is not None:
            s.leads_found = leads_found
        if contacted is not None:
            s.contacted = contacted
        if rejected is not None:
            s.rejected = rejected
        if fresh_leads is not None:
            s.fresh_leads = fresh_leads
        return s


class InMemoryLeadRepo:
    def __init__(self) -> None:
        self.items: list[Lead] = []

    async def save(self, lead: Lead) -> Lead:
        self.items.append(lead)
        return lead

    async def get(self, lead_id: UUID) -> Lead | None:
        return next((item for item in self.items if item.id == lead_id), None)

    async def list(
        self,
        search_id: UUID | None = None,
        stage: str | None = None,
    ) -> list[Lead]:
        items = list(self.items)
        if search_id is not None:
            items = [lead for lead in items if lead.search_id == search_id]
        if stage is not None:
            items = [lead for lead in items if lead.stage.value == stage]
        return items

    async def update_stage(self, lead_id: UUID, stage: str) -> Lead | None:
        lead = await self.get(lead_id)
        if lead is None:
            return None
        lead.stage = LeadStage(stage)
        return lead


def test_provider_factory_selects_openrouter_when_api_key_present() -> None:
    settings = Settings(
        llm_provider="openrouter",
        openrouter_api_key="sk-or-v1-test",
        openrouter_model="anthropic/claude-sonnet-4.5",
        openrouter_base_url="https://openrouter.ai/api/v1",
    )
    provider = create_llm_provider(settings)
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.provider_name == "openrouter"
    assert provider.model_name == "anthropic/claude-sonnet-4.5"


def test_provider_factory_falls_back_when_no_key() -> None:
    settings = Settings(openrouter_api_key="", llm_api_key="")
    provider = create_llm_provider(settings)
    assert isinstance(provider, FallbackHeuristicProvider)
    assert provider.provider_name == "fallback"


def test_agent_runner_executes_tool_loop_agnostically() -> None:
    called_with: list[str] = []

    async def enrich_company(company: str) -> dict[str, str]:
        called_with.append(company)
        return {"company": company, "status": "qualified"}

    tool = ToolDefinition(
        name="enrich_company",
        description="Enrich a company",
        parameters={"type": "object", "properties": {"company": {"type": "string"}}},
        handler=enrich_company,
    )
    runner = AgentRunner(FakeLLMProvider(), tools=[tool])
    result = asyncio.run(runner.run("Find and enrich Acme Cloud"))

    assert result.output == "Done"
    assert result.steps == 2
    assert result.provider == "custom-provider"
    assert called_with == ["Acme Cloud"]


def test_discover_leads_agent_use_case_persists_leads() -> None:
    search = Search(id=uuid4(), query="B2B SaaS · 50-200 employees", location="Colombia")
    searches = InMemorySearchRepo(search)
    leads = InMemoryLeadRepo()
    use_case = DiscoverLeadsAgentUseCase(
        llm=FallbackHeuristicProvider(),
        searches=searches,
        leads=leads,
    )

    result, saved = asyncio.run(use_case.execute(search.id))
    assert result.steps == 2
    assert len(saved) == 2
    assert search.status == "done"
    assert search.leads_found == 2
    assert saved[0].location == "Colombia"


def test_discover_leads_raises_not_found_for_missing_search() -> None:
    search = Search(id=uuid4(), query="B2B SaaS", location="Colombia")
    use_case = DiscoverLeadsAgentUseCase(
        llm=FallbackHeuristicProvider(),
        searches=InMemorySearchRepo(search),
        leads=InMemoryLeadRepo(),
    )
    with pytest.raises(NotFoundError):
        asyncio.run(use_case.execute(uuid4()))
