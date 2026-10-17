from typing import Protocol
from uuid import UUID

from dealcompass_api.domain.leads import Lead, Search


class SearchRepository(Protocol):
    async def save(self, search: Search) -> Search: ...

    async def get(self, search_id: UUID) -> Search | None: ...

    async def list(self) -> list[Search]: ...


class LeadRepository(Protocol):
    async def list(self, search_id: UUID | None = None) -> list[Lead]: ...


class JobQueue(Protocol):
    async def enqueue(self, kind: str, payload: dict) -> None: ...
