"""Discover companies for a search.

TODO: call Google Maps SDK (companies) -> Apify/org chart -> Dapta (contact),
then insert ``LeadModel`` rows. Currently only marks the search as done.
"""

import logging
from uuid import UUID

from dealcompass_api.infra.db.base import SessionFactory
from dealcompass_api.infra.db.models import SearchModel

logger = logging.getLogger(__name__)


async def handle(payload: dict) -> None:
    search_id = UUID(payload["search_id"])
    async with SessionFactory() as session:
        search = await session.get(SearchModel, search_id)
        if search is None:
            raise ValueError(f"Search {search_id} not found")
        logger.info("Discovering companies for %r in %r", search.query, search.location)
        search.status = "done"
        await session.commit()
