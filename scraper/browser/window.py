import logging
from typing import List
from playwright.async_api import BrowserContext

logger = logging.getLogger(__name__)


class WindowManager:
    """
    Support for multiple browser windows.
    Tracks created browser contexts as separate windows.
    """

    def __init__(self):
        self._windows: List[BrowserContext] = []

    def track(self, context: BrowserContext):
        """Register a context as a tracked window."""
        self._windows.append(context)

    @property
    def windows(self) -> List[BrowserContext]:
        """Return all tracked windows."""
        return list(self._windows)

    async def close_all(self):
        """Close all tracked windows."""
        for ctx in self._windows:
            try:
                await ctx.close()
            except Exception as e:
                logger.debug(f"Error closing window: {e}")
        self._windows.clear()
