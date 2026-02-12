import logging
from playwright.async_api import BrowserContext, Page

logger = logging.getLogger(__name__)


async def create_tab(context: BrowserContext) -> Page:
    """
    Creates a new page (tab) in the given browser context.
    """
    page = await context.new_page()
    return page
