"""
JSON-LD extraction and field-level extractors that prefer JSON-LD data
with CSS selector fallbacks.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from playwright.async_api import Page

from scraper.adapters.indeed.utils import safe_extract
from scraper.adapters.indeed.selectors import (
    TITLE_SELECTORS,
    COMPANY_SELECTORS,
    LOCATION_DETAIL_SELECTORS,
    DESCRIPTION_SELECTOR,
    JSON_LD_SELECTOR,
)

logger = logging.getLogger(__name__)


async def extract_json_ld(page: Page) -> Optional[Dict[str, Any]]:
    """
    Extract JSON-LD structured data from script tag.
    JSON-LD is stable W3C standard used for SEO.
    """
    try:
        scripts = await page.locator(JSON_LD_SELECTOR).all()
        for script in scripts:
            content = await script.inner_text()
            try:
                data = json.loads(content)
                # Check if it's a JobPosting schema
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    return data
            except json.JSONDecodeError:
                continue
    except Exception as e:
        logger.warning(f"Failed to extract JSON-LD: {e}")
    return None


async def extract_title(page: Page, json_ld: Optional[Dict] = None) -> str:
    """Extract title from JSON-LD or stable CSS selectors"""
    if json_ld and "title" in json_ld:
        return json_ld["title"]

    return await safe_extract(page, TITLE_SELECTORS, "title")


async def extract_company(page: Page, json_ld: Optional[Dict] = None) -> str:
    """Extract company from JSON-LD or stable CSS selectors"""
    if json_ld and "hiringOrganization" in json_ld:
        org = json_ld["hiringOrganization"]
        if isinstance(org, dict) and "name" in org:
            return org["name"]

    return await safe_extract(page, COMPANY_SELECTORS, "company")


async def extract_location(page: Page, json_ld: Optional[Dict] = None) -> str:
    """Extract location from JSON-LD or stable CSS selectors"""
    if json_ld and "jobLocation" in json_ld:
        loc = json_ld["jobLocation"]
        if isinstance(loc, dict) and "address" in loc:
            addr = loc["address"]
            if isinstance(addr, dict):
                city = addr.get("addressLocality", "")
                region = addr.get("addressRegion", "")
                return f"{city}, {region}".strip(", ")

    return await safe_extract(page, LOCATION_DETAIL_SELECTORS, "location")


async def extract_description(page: Page, json_ld: Optional[Dict] = None) -> str:
    """Extract description from JSON-LD or stable ID selector"""
    if json_ld and "description" in json_ld:
        return json_ld["description"]

    try:
        # #jobDescriptionText is stable ID that rarely changes
        container = page.locator(DESCRIPTION_SELECTOR)
        if await container.count() > 0:
            return await container.inner_text()
    except Exception as e:
        logger.warning(f"Failed to extract description: {e}")

    return ""
