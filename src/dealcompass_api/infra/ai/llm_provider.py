import json
import logging
from typing import Any
from uuid import uuid4

from openai import AsyncOpenAI

from dealcompass_api.config import Settings, get_settings
from dealcompass_api.domain.agent import Message, Role, ToolCall, ToolDefinition

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider:
    """Provider-agnostic LLM adapter using OpenAI-compatible APIs (OpenRouter primary)."""

    def __init__(
        self,
        *,
        provider_name: str = "openrouter",
        api_key: str,
        model_name: str = "anthropic/claude-sonnet-4.5",
        base_url: str = "https://openrouter.ai/api/v1",
        app_url: str = "http://localhost:5173",
        app_title: str = "DealCompass",
    ) -> None:
        self.provider_name = provider_name
        self.model_name = model_name
        headers: dict[str, str] = {}
        if provider_name.lower() == "openrouter":
            headers["HTTP-Referer"] = app_url
            headers["X-Title"] = app_title

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=headers or None,
        )

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.2,
    ) -> Message:
        api_messages = [self._serialize_message(m) for m in messages]
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": api_messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]
            kwargs["tool_choice"] = "auto"

        response = await self._client.chat.completions.create(**kwargs)
        if not response.choices:
            return Message(role=Role.ASSISTANT, content="")
        choice = response.choices[0].message

        parsed_tool_calls: list[ToolCall] = []
        if choice.tool_calls:
            for tc in choice.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {"raw": tc.function.arguments}
                parsed_tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=args if isinstance(args, dict) else {"value": args},
                    )
                )

        return Message(
            role=Role.ASSISTANT,
            content=choice.content or "",
            tool_calls=parsed_tool_calls,
        )

    @staticmethod
    def _serialize_message(msg: Message) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "role": msg.role.value,
            "content": msg.content or "",
        }
        if msg.role == Role.ASSISTANT and msg.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in msg.tool_calls
            ]
        if msg.role == Role.TOOL and msg.tool_call_id:
            payload["tool_call_id"] = msg.tool_call_id
            if msg.name:
                payload["name"] = msg.name
        return payload


class FallbackHeuristicProvider:
    """Offline fallback provider when no API key is configured, preserving the agentic loop."""

    def __init__(self, model_name: str = "heuristic-fallback") -> None:
        self.provider_name = "fallback"
        self.model_name = model_name

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.2,
    ) -> Message:
        has_tool_results = any(m.role == Role.TOOL for m in messages)
        user_text = next((m.content for m in reversed(messages) if m.role == Role.USER), "")

        if tools and not has_tool_results:
            save_tool = next((t for t in tools if t.name == "save_discovered_leads"), tools[0])
            if save_tool.name == "save_discovered_leads":
                return Message(
                    role=Role.ASSISTANT,
                    content="Analyzing ICP criteria and saving discovered leads.",
                    tool_calls=[
                        ToolCall(
                            id=f"call_{uuid4().hex[:8]}",
                            name="save_discovered_leads",
                            arguments={
                                "leads": [
                                    {
                                        "name": "Camila Vega",
                                        "role": "VP of Revenue",
                                        "company": "Kinetix Cloud",
                                        "website": "https://kinetixcloud.io",
                                        "industry": "B2B SaaS",
                                        "company_size": "50–200 employees",
                                        "score": 94,
                                        "email": "camila@kinetixcloud.io",
                                        "linkedin": "linkedin.com/in/camila-vega",
                                    },
                                    {
                                        "name": "Mateo Silva",
                                        "role": "Head of Growth",
                                        "company": "Altiplano Pay",
                                        "website": "https://altiplanopay.com",
                                        "industry": "Fintech",
                                        "company_size": "20–100 employees",
                                        "score": 89,
                                        "email": "mateo@altiplanopay.com",
                                        "linkedin": "linkedin.com/in/mateo-silva",
                                    },
                                ]
                            },
                        )
                    ],
                )

        if has_tool_results:
            last_tool = next((m.content for m in reversed(messages) if m.role == Role.TOOL), "")
            return Message(
                role=Role.ASSISTANT,
                content=f"Completed agentic workflow. Tool output: {last_tool}",
            )

        return Message(
            role=Role.ASSISTANT,
            content=f"Processed request for: {user_text[:200]}",
        )


def create_llm_provider(
    settings: Settings | None = None,
) -> OpenAICompatibleProvider | FallbackHeuristicProvider:
    cfg = settings or get_settings()
    api_key = cfg.resolved_llm_api_key.strip()
    if not api_key:
        logger.warning(
            "No LLM API key configured (OPENROUTER_API_KEY / LLM_API_KEY); "
            "using FallbackHeuristicProvider"
        )
        return FallbackHeuristicProvider(model_name=cfg.resolved_llm_model)

    return OpenAICompatibleProvider(
        provider_name=cfg.llm_provider,
        api_key=api_key,
        model_name=cfg.resolved_llm_model,
        base_url=cfg.resolved_llm_base_url,
        app_url=cfg.frontend_origin,
        app_title=cfg.app_name,
    )
