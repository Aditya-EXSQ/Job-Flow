from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import json
import logging
import re
from playwright.async_api import BrowserContext, Page
from scraper.core.models import Job

logger = logging.getLogger(__name__)


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

    # --- Optional base helpers for reuse across adapters ---

    def _extract_json_from_script(
        self, html: str, pattern: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from script tags using regex pattern.
        Returns None if extraction or parsing fails.
        Generic utility available to all adapters.
        """
        try:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Failed to parse JSON from script: {e}")
        return None

    async def _safe_extract(
        self, page: Page, selectors: List[str], field_name: str
    ) -> str:
        """
        Try multiple selectors in order, return first match or 'Unknown'.
        Handles both CSS and XPath selectors.
        Generic utility available to all adapters.
        """
        for selector in selectors:
            try:
                if selector.startswith("//") or selector.startswith("xpath="):
                    if not selector.startswith("xpath="):
                        selector = f"xpath={selector}"
                    loc = page.locator(selector)
                else:
                    loc = page.locator(selector)

                if await loc.count() > 0:
                    text = await loc.first.inner_text()
                    if text and text.strip():
                        return text.strip()
            except Exception as e:
                logger.debug(f"Selector '{selector}' failed for {field_name}: {e}")
                continue

        logger.warning(f"All selectors failed for {field_name}")
        return f"Unknown {field_name.title()}"
