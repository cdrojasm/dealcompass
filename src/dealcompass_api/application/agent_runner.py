import json
import logging
from typing import Any
from uuid import UUID

from dealcompass_api.application.ports import LeadRepository, LLMProvider, SearchRepository
from dealcompass_api.domain.agent import AgentResult, Message, Role, ToolDefinition
from dealcompass_api.domain.leads import Lead, LeadStage, NotFoundError

logger = logging.getLogger(__name__)

DEFAULT_AGENT_SYSTEM_PROMPT = (
    "You are DealCompass Agent, an autonomous B2B sales prospecting and ICP qualification "
    "agent. Use available tools when needed to discover, qualify, and persist high-fit B2B leads."
)


class AgentRunner:
    """Provider-agnostic multi-step tool-calling agentic loop."""

    def __init__(
        self,
        llm: LLMProvider,
        *,
        system_prompt: str = DEFAULT_AGENT_SYSTEM_PROMPT,
        tools: list[ToolDefinition] | None = None,
        max_steps: int = 5,
    ) -> None:
        self._llm = llm
        self._system_prompt = system_prompt
        self._tools = tools or []
        self._tool_map = {t.name: t for t in self._tools}
        self._max_steps = max_steps

    async def run(self, user_prompt: str) -> AgentResult:
        messages: list[Message] = [
            Message(role=Role.SYSTEM, content=self._system_prompt),
            Message(role=Role.USER, content=user_prompt),
        ]

        steps = 0
        for step in range(1, self._max_steps + 1):
            steps = step
            response = await self._llm.complete(messages, tools=self._tools or None)
            messages.append(response)

            if not response.tool_calls:
                return AgentResult(
                    output=response.content,
                    messages=messages,
                    steps=steps,
                    provider=self._llm.provider_name,
                    model=self._llm.model_name,
                )

            for call in response.tool_calls:
                tool = self._tool_map.get(call.name)
                if tool is None:
                    tool_output: Any = {"error": f"Unknown tool: {call.name}"}
                else:
                    try:
                        tool_output = await tool.handler(**call.arguments)
                    except Exception as exc:
                        logger.exception("Tool %s failed", call.name)
                        tool_output = {"error": str(exc)}

                serialized = (
                    tool_output
                    if isinstance(tool_output, str)
                    else json.dumps(tool_output, ensure_ascii=False)
                )
                messages.append(
                    Message(
                        role=Role.TOOL,
                        tool_call_id=call.id,
                        name=call.name,
                        content=serialized,
                    )
                )

        final_text = messages[-1].content if messages else ""
        return AgentResult(
            output=final_text,
            messages=messages,
            steps=steps,
            provider=self._llm.provider_name,
            model=self._llm.model_name,
        )


class DiscoverLeadsAgentUseCase:
    """Agentic workflow that discovers and qualifies B2B leads for a Search run."""

    def __init__(
        self,
        llm: LLMProvider,
        searches: SearchRepository,
        leads: LeadRepository,
    ) -> None:
        self._llm = llm
        self._searches = searches
        self._leads = leads

    async def execute(self, search_id: UUID) -> tuple[AgentResult, list[Lead]]:
        search = await self._searches.get(search_id)
        if search is None:
            raise NotFoundError(f"Search {search_id} not found")

        saved_leads: list[Lead] = []

        async def save_discovered_leads(leads: list[dict[str, Any]]) -> dict[str, Any]:
            for item in leads:
                company = str(item.get("company") or "").strip()
                if not company:
                    continue
                score = int(item.get("score") or 85)
                lead = await self._leads.save(
                    Lead(
                        search_id=search.id,
                        icp_id=search.icp_id,
                        name=str(item.get("name") or "").strip(),
                        role=str(item.get("role") or "").strip(),
                        company=company,
                        website=item.get("website"),
                        industry=str(item.get("industry") or "").strip(),
                        company_size=str(item.get("company_size") or "").strip(),
                        location=str(item.get("location") or search.location).strip(),
                        score=max(0, min(100, score)),
                        stage=LeadStage.DISCOVERED,
                        email=item.get("email"),
                        linkedin=item.get("linkedin"),
                    )
                )
                saved_leads.append(lead)
            return {"saved_count": len(saved_leads), "search_id": str(search.id)}

        save_tool = ToolDefinition(
            name="save_discovered_leads",
            description="Persist discovered and ICP-qualified B2B leads for the current search.",
            parameters={
                "type": "object",
                "properties": {
                    "leads": {
                        "type": "array",
                        "description": (
                            "List of qualified B2B prospect leads matching the ICP and location."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Decision maker full name",
                                },
                                "role": {"type": "string", "description": "Job title / role"},
                                "company": {"type": "string", "description": "Company name"},
                                "website": {"type": "string", "description": "Company website URL"},
                                "industry": {"type": "string", "description": "Company industry"},
                                "company_size": {
                                    "type": "string",
                                    "description": "Employee headcount range",
                                },
                                "location": {
                                    "type": "string",
                                    "description": "City / country location",
                                },
                                "score": {
                                    "type": "integer",
                                    "description": "ICP fit score from 0 to 100",
                                },
                                "email": {"type": "string", "description": "Work email address"},
                                "linkedin": {
                                    "type": "string",
                                    "description": "LinkedIn profile path",
                                },
                            },
                            "required": [
                                "name",
                                "role",
                                "company",
                                "industry",
                                "company_size",
                                "score",
                            ],
                        },
                    }
                },
                "required": ["leads"],
            },
            handler=save_discovered_leads,
        )

        runner = AgentRunner(
            llm=self._llm,
            system_prompt=(
                "You are DealCompass Lead Discovery Agent. Given an ICP query and target "
                "location, identify 3 to 5 realistic, high-fit B2B companies and decision "
                "makers in that location, score their ICP fit (0-100), and call "
                "`save_discovered_leads` to persist them."
            ),
            tools=[save_tool],
            max_steps=4,
        )

        prompt = (
            f"Run B2B lead discovery for ICP criteria: '{search.query}' "
            f"in target location: '{search.location}'. "
            "Call save_discovered_leads with the qualified prospects."
        )
        result = await runner.run(prompt)

        all_leads = await self._leads.list(search.id)
        contacted_count = sum(
            1 for item in all_leads if item.stage in (LeadStage.CONTACTED, LeadStage.QUALIFICATION)
        )
        rejected_count = sum(1 for item in all_leads if item.stage == LeadStage.DISCARDED)
        await self._searches.update_status(
            search.id,
            status="done",
            leads_found=len(all_leads),
            contacted=contacted_count,
            rejected=rejected_count,
            fresh_leads=len(saved_leads),
        )
        return result, saved_leads
