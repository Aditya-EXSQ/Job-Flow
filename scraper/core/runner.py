import logging
from typing import List, Dict, Type
from scraper.browser.manager import BrowserManager
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

            # Discover jobs - now returns job data directly from clicking on each job
            jobs_data = await adapter.discover_jobs()
            logger.info(f"Discovered {len(jobs_data)} jobs.")

            # Convert job data dictionaries to Job objects
            jobs: List[Job] = []
            for job_dict in jobs_data:
                try:
                    # Create Job object from the extracted data
                    job = Job(
                        id=job_dict.get("jobkey", "unknown"),
                        title=job_dict.get("title", "Unknown Title"),
                        company="Unknown Company",  # Not extracted in discovery
                        location="Unknown Location",  # Not extracted in discovery
                        description=job_dict.get("description", ""),
                        source="indeed",
                        url=f"https://in.indeed.com/viewjob?jk={job_dict.get('jobkey', '')}",
                        salary=None,
                        posted_at=None,
                    )
                    jobs.append(job)
                except Exception as e:
                    logger.error(f"Failed to create Job object: {e}")

            logger.info(f"Successfully scraped {len(jobs)} jobs.")

            # In a real system, we would save to DB/File here.
            for job in jobs:
                print(job)  # Output to stdout for verification

        except Exception as e:
            logger.exception(f"Runner failed: {e}")
        finally:
            await BrowserManager.close()


runner = Runner()
