from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


class LeadStage(StrEnum):
    DISCOVERED = "discovered"
    CONTACTED = "contacted"
    QUALIFICATION = "qualification"
    DISCARDED = "discarded"


@dataclass(slots=True)
class Search:
    query: str
    location: str
    id: UUID = field(default_factory=uuid4)
    status: str = "queued"
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("Search query cannot be empty")
        if not self.location.strip():
            raise ValueError("Search location cannot be empty")


@dataclass(slots=True)
class Lead:
    search_id: UUID
    company: str
    id: UUID = field(default_factory=uuid4)
    website: str | None = None
    stage: LeadStage = LeadStage.DISCOVERED
    created_at: datetime | None = None
