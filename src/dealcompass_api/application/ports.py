from typing import Protocol
from uuid import UUID

from dealcompass_api.domain.leads import Icp, Lead, Search


class IcpRepository(Protocol):
    async def save(self, icp: Icp) -> Icp: ...

    async def get(self, icp_id: UUID) -> Icp | None: ...

    async def list(self) -> list[Icp]: ...


class SearchRepository(Protocol):
    async def save(self, search: Search) -> Search: ...

    async def get(self, search_id: UUID) -> Search | None: ...

    async def list(self) -> list[Search]: ...


class LeadRepository(Protocol):
    async def list(self, search_id: UUID | None = None) -> list[Lead]: ...


class JobQueue(Protocol):
    async def enqueue(self, kind: str, payload: dict) -> None: ...
