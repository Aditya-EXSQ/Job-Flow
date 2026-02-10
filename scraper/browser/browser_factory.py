import logging
from playwright.async_api import Browser, Playwright

from scraper.config.settings import settings

logger = logging.getLogger(__name__)

# Browser launch arguments to avoid detection
LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--disable-web-security",
    "--disable-features=IsolateOrigins,site-per-process",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-accelerated-2d-canvas",
    "--no-first-run",
    "--no-zygote",
    "--disable-gpu",
    "--hide-scrollbars",
    "--mute-audio",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
]


async def create_browser(playwright: Playwright) -> Browser:
    """
    Launch a Chromium browser instance with anti-detection args.
    """
    browser = await playwright.chromium.launch(
        headless=settings.HEADLESS,
        args=LAUNCH_ARGS,
    )
    logger.info(f"Browser launched (Headless: {settings.HEADLESS}).")
    return browser
