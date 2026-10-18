from sqlalchemy.ext.asyncio import AsyncSession

from dealcompass_api.application.agent_runner import AgentRunner, DiscoverLeadsAgentUseCase
from dealcompass_api.application.create_search import CreateSearchUseCase
from dealcompass_api.application.ports import LLMProvider
from dealcompass_api.infra.ai.llm_provider import create_llm_provider
from dealcompass_api.infra.repositories.search_repository import (
    SqlAlchemyIcpRepository,
    SqlAlchemyJobQueue,
    SqlAlchemyLeadRepository,
    SqlAlchemySearchRepository,
)


class LeadsFactory:
    """Composition root for the lead-generation and agentic use cases."""

    @staticmethod
    def llm() -> LLMProvider:
        return create_llm_provider()

    @staticmethod
    def agent(system_prompt: str | None = None) -> AgentRunner:
        llm = create_llm_provider()
        if system_prompt:
            return AgentRunner(llm, system_prompt=system_prompt)
        return AgentRunner(llm)

    @staticmethod
    def discover_leads(session: AsyncSession) -> DiscoverLeadsAgentUseCase:
        return DiscoverLeadsAgentUseCase(
            llm=create_llm_provider(),
            searches=SqlAlchemySearchRepository(session),
            leads=SqlAlchemyLeadRepository(session),
        )

    @staticmethod
    def create_search(session: AsyncSession) -> CreateSearchUseCase:
        return CreateSearchUseCase(
            SqlAlchemySearchRepository(session),
            SqlAlchemyJobQueue(session),
            SqlAlchemyIcpRepository(session),
        )

    @staticmethod
    def icps(session: AsyncSession) -> SqlAlchemyIcpRepository:
        return SqlAlchemyIcpRepository(session)

    @staticmethod
    def searches(session: AsyncSession) -> SqlAlchemySearchRepository:
        return SqlAlchemySearchRepository(session)

    @staticmethod
    def leads(session: AsyncSession) -> SqlAlchemyLeadRepository:
        return SqlAlchemyLeadRepository(session)
