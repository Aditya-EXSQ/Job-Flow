"""
Extract job cards from window.mosaic.providerData embedded in page.
This is Indeed's primary data structure for search results.
"""

import logging
from typing import List, Dict, Any
from playwright.async_api import Page

from scraper.adapters.indeed.utils import extract_json_from_script

logger = logging.getLogger(__name__)

# Pattern matches: window.mosaic.providerData["mosaic-provider-jobcards"]={...}
MOSAIC_PATTERN = (
    r'window\.mosaic\.providerData\["mosaic-provider-jobcards"\]\s*=\s*({.*?});'
)


async def extract_mosaic_data(page: Page) -> List[Dict[str, Any]]:
    """
    Extract job cards from window.mosaic.providerData embedded in page.
    This is Indeed's primary data structure for search results.
    """
    try:
        html = await page.content()
        data = extract_json_from_script(html, MOSAIC_PATTERN)

        if (
            data
            and "metaData" in data
            and "mosaicProviderJobCardsModel" in data["metaData"]
        ):
            job_cards = data["metaData"]["mosaicProviderJobCardsModel"].get(
                "results", []
            )
            logger.info(f"Extracted {len(job_cards)} jobs from mosaic data")
            return job_cards
    except Exception as e:
        logger.warning(f"Failed to extract mosaic data: {e}")
    return []
