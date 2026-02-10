"""
IndeedAdapter - Job portal adapter for Indeed.com

Implements JobPortalAdapter interface. Delegates all work to submodules:
- discovery.py for job URL discovery from SERP
- scraping.py for individual job detail extraction
"""

import logging
from typing import List, Set
from playwright.async_api import BrowserContext

from scraper.adapters.base import JobPortalAdapter
from scraper.core.models import Job
from scraper.adapters.indeed.config import (
    BASE_URL,
    SEARCH_URL,
    MAX_PAGES,
    JOBS_PER_PAGE,
)
from scraper.adapters.indeed import discovery as discovery_module
from scraper.adapters.indeed import scraping as scraping_module

logger = logging.getLogger(__name__)


class IndeedAdapter(JobPortalAdapter):
    """
    Indeed adapter using embedded JSON extraction with stable CSS fallbacks.
    Resilient to HTML changes by preferring JSON-LD and window data over DOM selectors.
    """

    BASE_URL = BASE_URL
    SEARCH_URL = SEARCH_URL
    MAX_PAGES = MAX_PAGES
    JOBS_PER_PAGE = JOBS_PER_PAGE

    def __init__(
        self, context, query: str = "software engineer", location: str = "remote"
    ):
        super().__init__(context)
        self.query = query
        self.location = location
        self.seen_jks: Set[str] = set()

    async def discover_jobs(self) -> List[str]:
        """
        Discover job URLs from Indeed SERP with pagination support.
        Extracts from embedded JSON first, falls back to DOM selectors.
        """
        return await discovery_module.discover_jobs(
            self.context, self.query, self.location, self.seen_jks
        )

    async def scrape_job(self, url: str) -> Job:
        """
        Scrape job details using JSON-LD first, CSS selectors as fallback.
        Never crashes - returns partial data with warnings.
        """
        return await scraping_module.scrape_job(self.context, url)

    async def scrape_jobs_batch(
        self, job_urls: List[str], max_concurrent: int = 5
    ) -> List[Job]:
        """
        Scrape multiple jobs concurrently using a batch/queue approach.
        Opens up to max_concurrent tabs at a time to avoid overwhelming the browser.
        """
        return await scraping_module.scrape_jobs_batch(
            self.context, job_urls, max_concurrent
        )

    # --- Internal methods exposed for backward compatibility with tests ---

    async def _extract_jobs_from_dom(self, page):
        """Backward compat: delegates to extraction.dom module."""
        from scraper.adapters.indeed.extraction.dom import extract_jobs_from_dom

        return await extract_jobs_from_dom(page)

    async def _extract_json_ld(self, page):
        """Backward compat: delegates to extraction.json_ld module."""
        from scraper.adapters.indeed.extraction.json_ld import extract_json_ld

        return await extract_json_ld(page)

    async def _extract_title(self, page, json_ld=None):
        """Backward compat: delegates to extraction.json_ld module."""
        from scraper.adapters.indeed.extraction.json_ld import extract_title

        return await extract_title(page, json_ld)

    async def _extract_company(self, page, json_ld=None):
        """Backward compat: delegates to extraction.json_ld module."""
        from scraper.adapters.indeed.extraction.json_ld import extract_company

        return await extract_company(page, json_ld)

    async def _extract_location(self, page, json_ld=None):
        """Backward compat: delegates to extraction.json_ld module."""
        from scraper.adapters.indeed.extraction.json_ld import extract_location

        return await extract_location(page, json_ld)

    async def _extract_description(self, page, json_ld=None):
        """Backward compat: delegates to extraction.json_ld module."""
        from scraper.adapters.indeed.extraction.json_ld import extract_description

        return await extract_description(page, json_ld)

    async def _extract_salary(self, page, json_ld=None):
        """Backward compat: delegates to extraction.salary module."""
        from scraper.adapters.indeed.extraction.salary import extract_salary

        return await extract_salary(page, json_ld)

    async def _detect_bot_challenge(self, page):
        """Backward compat: delegates to discovery module."""
        return await discovery_module.detect_bot_challenge(page)

    async def _scroll_to_load_all_jobs(self, page):
        """Backward compat: delegates to discovery module."""
        return await discovery_module.scroll_to_load_all_jobs(page)

    def _extract_json_from_script(self, html, pattern):
        """Backward compat: delegates to utils module."""
        from scraper.adapters.indeed.utils import extract_json_from_script

        return extract_json_from_script(html, pattern)

    async def _safe_extract(self, page, selectors, field_name):
        """Backward compat: delegates to utils module."""
        from scraper.adapters.indeed.utils import safe_extract

        return await safe_extract(page, selectors, field_name)

    async def _extract_mosaic_data(self, page):
        """Backward compat: delegates to extraction.mosaic module."""
        from scraper.adapters.indeed.extraction.mosaic import extract_mosaic_data

        return await extract_mosaic_data(page)

    async def _extract_job_from_page(self, page, url):
        """Backward compat: delegates to scraping module."""
        return await scraping_module.extract_job_from_page(page, url)
