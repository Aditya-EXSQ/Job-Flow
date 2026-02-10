import asyncio
import logging
from typing import List, Dict, Type
from scraper.core.browser import BrowserManager
from scraper.adapters.base import JobPortalAdapter
from scraper.adapters.indeed import IndeedAdapter
from scraper.core.models import Job

logger = logging.getLogger(__name__)

ADAPTERS: Dict[str, Type[JobPortalAdapter]] = {
    "indeed": IndeedAdapter,
}


class Runner:
    """
    Orchestrates the scraping process across different portals.
    """

    async def run(self, portal: str, query: str, location: str):
        """
        Run the scraper for a specific portal.
        """
        adapter_cls = ADAPTERS.get(portal.lower())
        if not adapter_cls:
            raise ValueError(
                f"Portal '{portal}' not supported. Available portals: {list(ADAPTERS.keys())}"
            )

        try:
            # Initialize browser
            await BrowserManager.initialize()
            context = await BrowserManager.get_context()

            # Initialize adapter with the shared context
            adapter = adapter_cls(context)  # type: ignore
            # Dynamically set query and location if the adapter supports it
            if hasattr(adapter, "query"):
                adapter.query = query
            if hasattr(adapter, "location"):
                adapter.location = location

            logger.info(
                f"Starting discovery for {portal} (Query: {query}, Location: {location})"
            )

            # Discover jobs
            job_urls = await adapter.discover_jobs()
            logger.info(f"Discovered {len(job_urls)} jobs.")

            # Scrape jobs concurrently
            tasks = [adapter.scrape_job(url) for url in job_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            jobs: List[Job] = []
            for res in results:
                if isinstance(res, Job):
                    jobs.append(res)
                elif isinstance(res, Exception):
                    logger.error(f"Job scraping failed: {res}")

            logger.info(f"Successfully scraped {len(jobs)} jobs.")

            # In a real system, we would save to DB/File here.
            for job in jobs:
                print(job)  # Output to stdout for verification

        except Exception as e:
            logger.exception(f"Runner failed: {e}")
        finally:
            await BrowserManager.close()


runner = Runner()
