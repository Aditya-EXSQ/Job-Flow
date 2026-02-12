"""
Small helper functions used across the Indeed adapter.
No scraping logic — only text processing and data extraction utilities.
"""

import json
import logging
import re
from typing import Optional, Dict, Any, List
from playwright.async_api import Page

logger = logging.getLogger(__name__)


def extract_json_from_script(html: str, pattern: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from script tags using regex pattern.
    Returns None if extraction or parsing fails.
    """
    try:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            json_str = match.group(1)
            return json.loads(json_str)
    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning(f"Failed to parse JSON from script: {e}")
    return None


async def safe_extract(page: Page, selectors: List[str], field_name: str) -> str:
    """
    Try multiple selectors in order, return first match or 'Unknown'.
    Handles both CSS and XPath selectors.
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
