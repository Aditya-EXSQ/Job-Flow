"""
Browser Context Factory

Minimal context configuration that lets real Chrome manage its own fingerprint.
Removes manual overrides that create inconsistencies detectable by anti-bot systems.
"""

import logging
from typing import Optional
from playwright.async_api import Browser, BrowserContext

from scraper.config.settings import settings
from scraper.browser.proxy import get_proxy_config

logger = logging.getLogger(__name__)


async def create_context(
    browser: Browser,
    user_agent: Optional[str] = None,
) -> BrowserContext:
    """
    Create a browser context with minimal overrides.

    Why this reduces detection:
    - viewport=None allows natural window sizing (not static dimensions that fingerprint)
    - Removed Sec-Fetch-* headers: Chrome manages these natively based on navigation type
    - Removed Accept-Encoding, Connection: Chrome sets these based on capabilities
    - Removed screen/WebGL overrides: Creates inconsistencies when mismatched with real hardware
    - Removed plugin spoofing: Real Chrome has native plugin configuration
    - No timezone override: Uses system timezone (expected behavior)

    Only configures what's necessary:
    - user_agent: If custom UA needed for specific scraping target
    - locale: For language preference
    - proxy: If routing traffic through proxy

    Args:
        browser: Browser instance
        user_agent: Optional custom user agent (None = Chrome default)

    Returns:
        BrowserContext instance
    """
    proxy_config = get_proxy_config()

    # Build context config with only essential overrides
    context_config = {
        "viewport": None,  # Let browser use natural window size
        "locale": "en-US",
        "proxy": proxy_config,
        "ignore_https_errors": settings.IGNORE_HTTPS_ERRORS,
    }

    # Only set user_agent if explicitly provided
    if user_agent:
        context_config["user_agent"] = user_agent

    context = await browser.new_context(**context_config)

    logger.info("Browser context created with minimal fingerprint overrides")
    return context
