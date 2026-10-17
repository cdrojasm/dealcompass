"""Generic job worker backed by PostgreSQL.

Claims one pending job at a time with ``FOR UPDATE SKIP LOCKED`` so several
Railway replicas can run safely without a broker. Handlers are registered by
job ``kind`` in ``HANDLERS``.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy import select

from dealcompass_api.application.create_search import DISCOVER_COMPANIES
from dealcompass_api.config import get_settings
from dealcompass_api.infra.db import models  # noqa: F401 - registers ORM metadata
from dealcompass_api.infra.db.base import Base, SessionFactory, engine
from dealcompass_api.infra.db.models import JobModel, SearchModel
from dealcompass_api.workers.handlers import discover_companies

logger = logging.getLogger(__name__)

Handler = Callable[[dict], Awaitable[None]]
HANDLERS: dict[str, Handler] = {DISCOVER_COMPANIES: discover_companies.handle}
MAX_ATTEMPTS = 3


async def claim_and_run() -> bool:
    """Run one job. Returns False when the queue is empty."""
    async with SessionFactory() as session:
        job = await session.scalar(
            select(JobModel)
            .where(JobModel.status == "pending")
            .order_by(JobModel.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if job is None:
            return False
        job.attempts += 1
        try:
            await HANDLERS[job.kind](job.payload)
            job.status = "done"
            job.finished_at = datetime.now(UTC)
        except Exception as exc:
            logger.exception("Job %s (%s) failed", job.id, job.kind)
            job.error = str(exc)
            job.status = "failed" if job.attempts >= MAX_ATTEMPTS else "pending"
            if job.status == "failed" and job.kind == DISCOVER_COMPANIES:
                search = await session.get(SearchModel, job.payload.get("search_id"))
                if search:
                    search.status = "failed"
        await session.commit()
        return True


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    while True:
        if not await claim_and_run():
            await asyncio.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    asyncio.run(main())
