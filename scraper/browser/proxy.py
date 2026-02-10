import logging
from typing import Optional, Dict

from scraper.config.settings import settings

logger = logging.getLogger(__name__)


def get_proxy_config() -> Optional[Dict[str, str]]:
    """
    Build proxy configuration for the browser context.
    Returns ScrapeOps proxy config if API key is available, else None.
    """
    if settings.SCRAPEOPS_API_KEY:
        logger.info("Using ScrapeOps Proxy")
        return {
            "server": "http://proxy.scrapeops.io:5353",
            "username": "scrapeops",
            "password": settings.SCRAPEOPS_API_KEY,
        }
    else:
        logger.warning("SCRAPEOPS_API_KEY not found. No proxy will be used.")
        return None
