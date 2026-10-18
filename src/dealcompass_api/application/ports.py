from typing import Protocol
from uuid import UUID

from dealcompass_api.domain.agent import Message, ToolDefinition
from dealcompass_api.domain.leads import Icp, Lead, Search


class LLMProvider(Protocol):
    """Provider-agnostic interface for chat completion and tool-calling LLMs."""

    provider_name: str
    model_name: str

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.2,
    ) -> Message: ...


class IcpRepository(Protocol):
    async def save(self, icp: Icp) -> Icp: ...

    async def get(self, icp_id: UUID) -> Icp | None: ...

    async def list(self) -> list[Icp]: ...

    async def delete(self, icp_id: UUID) -> bool: ...


class SearchRepository(Protocol):
    async def save(self, search: Search) -> Search: ...

    async def get(self, search_id: UUID) -> Search | None: ...

    async def list(self, icp_id: UUID | None = None) -> list[Search]: ...

    async def update_status(
        self,
        search_id: UUID,
        status: str,
        leads_found: int | None = None,
        contacted: int | None = None,
        rejected: int | None = None,
        fresh_leads: int | None = None,
    ) -> Search | None: ...


class LeadRepository(Protocol):
    async def save(self, lead: Lead) -> Lead: ...

    async def get(self, lead_id: UUID) -> Lead | None: ...

    async def list(
        self,
        search_id: UUID | None = None,
        stage: str | None = None,
    ) -> list[Lead]: ...

    async def update_stage(self, lead_id: UUID, stage: str) -> Lead | None: ...


class JobQueue(Protocol):
    async def enqueue(self, kind: str, payload: dict) -> None: ...
