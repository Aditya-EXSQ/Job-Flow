from abc import ABC, abstractmethod
from typing import List
from playwright.async_api import BrowserContext
from scraper.core.models import Job


class JobPortalAdapter(ABC):
    """
    Abstract base class for all job portal adapters.
    """

    def __init__(self, context: BrowserContext):
        self.context = context

    @abstractmethod
    async def discover_jobs(self) -> List[str]:
        """
        Discover job detail URLs from the portal.
        Returns:
            List[str]: A list of job detail URLs.
        """
        pass

    @abstractmethod
    async def scrape_job(self, url: str) -> Job:
        """
        Scrape a single job detail page.
        Args:
            url (str): The URL of the job detail page.
        Returns:
            Job: The normalized Job object.
        """
        pass
