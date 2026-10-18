"""Discover companies and leads for a search using the provider-agnostic agentic workflow."""

import logging
from uuid import UUID

from dealcompass_api.infra.db.base import SessionFactory
from dealcompass_api.infra.factory.leads_factory import LeadsFactory

logger = logging.getLogger(__name__)


async def handle(payload: dict) -> None:
    search_id = UUID(payload["search_id"])
    async with SessionFactory() as session:
        result, saved_leads = await LeadsFactory.discover_leads(session).execute(search_id)
        logger.info(
            "Agent (%s/%s) completed search %s in %d steps; saved %d leads",
            result.provider,
            result.model,
            search_id,
            result.steps,
            len(saved_leads),
        )
