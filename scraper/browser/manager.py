import logging
from typing import Optional, AsyncGenerator
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)
from scraper.browser.user_agent import UserAgentProvider
from scraper.browser.launch import create_browser
from scraper.browser.context import create_context
from scraper.browser.tabs import create_tab

logger = logging.getLogger(__name__)


class BrowserManager:
    """
    Manages the lifecycle of the Playwright browser and context.
    """

    _playwright: Optional[Playwright] = None
    _browser: Optional[Browser] = None
    _context: Optional[BrowserContext] = None

    @classmethod
    async def initialize(cls):
        """
        Initializes the browser and context if not already running.
        """
        # Initialize user agent provider
        UserAgentProvider.initialize()

        if cls._playwright is None:
            cls._playwright = await async_playwright().start()
            logger.info("Playwright started.")

        if cls._browser is None:
            cls._browser = await create_browser(cls._playwright)

        if cls._context is None:
            # Generate a random user agent
            user_agent = UserAgentProvider.get_random()
            logger.info(f"Using User Agent: {user_agent}")

            cls._context = await create_context(cls._browser, user_agent)

    @classmethod
    async def get_context(cls) -> BrowserContext:
        """
        Returns the shared browser context. Initializes if necessary.
        """
        if cls._context is None:
            await cls.initialize()
        return cls._context

    @classmethod
    async def new_page(cls) -> Page:
        """
        Creates a new page in the shared context.
        """
        context = await cls.get_context()
        return await create_tab(context)

    @classmethod
    async def close(cls):
        """
        Closes the browser and stops Playwright.
        """
        if cls._context:
            await cls._context.close()
            cls._context = None
            logger.info("Browser context closed.")

        if cls._browser:
            await cls._browser.close()
            cls._browser = None
            logger.info("Browser closed.")

        if cls._playwright:
            await cls._playwright.stop()
            cls._playwright = None
            logger.info("Playwright stopped.")


async def get_browser_context() -> AsyncGenerator[BrowserContext, None]:
    """
    Context manager dependency for getting the browser context.
    Although we use a singleton manager, this allows for easier injection/testing.
    """
    await BrowserManager.initialize()
    if BrowserManager._context:  # Should be initialized
        yield BrowserManager._context
