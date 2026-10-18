from dataclasses import dataclass
from uuid import UUID

from dealcompass_api.application.ports import IcpRepository, JobQueue, SearchRepository
from dealcompass_api.domain.leads import NotFoundError, Search

DISCOVER_COMPANIES = "discover_companies"


@dataclass(frozen=True, slots=True)
class CreateSearchCommand:
    query: str
    location: str
    icp_id: UUID | None = None


class CreateSearchUseCase:
    def __init__(
        self,
        searches: SearchRepository,
        queue: JobQueue,
        icps: IcpRepository | None = None,
    ) -> None:
        self._searches = searches
        self._queue = queue
        self._icps = icps

    async def execute(self, command: CreateSearchCommand) -> Search:
        if command.icp_id is not None and self._icps is not None:
            icp = await self._icps.get(command.icp_id)
            if icp is None:
                raise NotFoundError(f"ICP {command.icp_id} not found")
        search = await self._searches.save(
            Search(query=command.query, location=command.location, icp_id=command.icp_id)
        )
        await self._queue.enqueue(DISCOVER_COMPANIES, {"search_id": str(search.id)})
        return search
