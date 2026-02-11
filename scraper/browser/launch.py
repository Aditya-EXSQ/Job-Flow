"""
Browser Launch Module

Simplified browser initialization using real Chrome for consistent fingerprinting.
Minimizes detection surface by removing unnecessary launch arguments.
"""

import logging
from playwright.async_api import Browser, Playwright

from scraper.config.settings import settings

logger = logging.getLogger(__name__)


async def create_browser(playwright: Playwright) -> Browser:
    """
    Launch a real Chrome browser instance.

    Why this reduces detection:
    - channel="chrome" uses system Chrome with native fingerprint (not bundled Chromium)
    - No custom launch args that create detectable patterns
    - Default Chrome behavior is harder to fingerprint than modified Chromium

    Args:
        playwright: Playwright instance

    Returns:
        Browser instance
    """
    browser = await playwright.chromium.launch(
        channel="chrome",  # Use real Chrome, not Chromium
        headless=settings.HEADLESS,  # Default to False for natural behavior
    )

    logger.info(f"Browser launched (Chrome, Headless: {settings.HEADLESS})")
    return browser
