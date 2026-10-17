from dataclasses import dataclass

from dealcompass_api.application.ports import JobQueue, SearchRepository
from dealcompass_api.domain.leads import Search

DISCOVER_COMPANIES = "discover_companies"


@dataclass(frozen=True, slots=True)
class CreateSearchCommand:
    query: str
    location: str


class CreateSearchUseCase:
    def __init__(self, searches: SearchRepository, queue: JobQueue) -> None:
        self._searches = searches
        self._queue = queue

    async def execute(self, command: CreateSearchCommand) -> Search:
        search = await self._searches.save(Search(query=command.query, location=command.location))
        await self._queue.enqueue(DISCOVER_COMPANIES, {"search_id": str(search.id)})
        return search
