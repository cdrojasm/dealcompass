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
class Icp:
    name: str
    industry: str = ""
    company_size: str = ""
    target_roles: str = ""
    id: UUID = field(default_factory=uuid4)
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("ICP name cannot be empty")


@dataclass(slots=True)
class Search:
    query: str
    location: str
    icp_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    status: str = "queued"
    leads_found: int = 0
    contacted: int = 0
    rejected: int = 0
    fresh_leads: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("Search query cannot be empty")
        if not self.location.strip():
            raise ValueError("Search location cannot be empty")


@dataclass(slots=True)
class Lead:
    search_id: UUID
    company: str
    icp_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    role: str = ""
    website: str | None = None
    industry: str = ""
    company_size: str = ""
    location: str = ""
    score: int = 0
    stage: LeadStage = LeadStage.DISCOVERED
    email: str | None = None
    linkedin: str | None = None
    last_activity_at: datetime | None = None
    created_at: datetime | None = None
