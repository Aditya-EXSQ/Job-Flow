import logging
from playwright.async_api import Browser, BrowserContext

from scraper.config.settings import settings
from scraper.browser.proxy import get_proxy_config
from scraper.browser.stealth import apply_stealth_scripts

logger = logging.getLogger(__name__)


async def create_context(
    browser: Browser,
    user_agent: str,
) -> BrowserContext:
    """
    Create a browser context with viewport, locale, headers, proxy, and stealth scripts.
    """
    proxy_config = get_proxy_config()

    context = await browser.new_context(
        user_agent=user_agent,
        viewport={"width": 1366, "height": 768},
        locale="en-US",
        timezone_id="America/New_York",
        proxy=proxy_config,
        ignore_https_errors=settings.IGNORE_HTTPS_ERRORS,
        extra_http_headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        },
    )

    # Apply stealth scripts to avoid bot detection
    await apply_stealth_scripts(context, user_agent)

    return context
