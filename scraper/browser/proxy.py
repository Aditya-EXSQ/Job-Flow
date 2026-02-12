import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict

from scraper.config.settings import settings

logger = logging.getLogger(__name__)


class ProxyProvider(ABC):
    """
    Abstract base class for proxy providers.
    Each provider implements its own configuration logic.
    """

    @abstractmethod
    def get_config(self) -> Optional[Dict[str, str]]:
        """
        Returns proxy configuration dict with 'server', 'username', 'password' keys,
        or None if proxy cannot be configured.
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Returns the display name of this proxy provider."""
        pass


class NoProxyProvider(ProxyProvider):
    """Provider that explicitly disables proxy usage."""

    def get_config(self) -> Optional[Dict[str, str]]:
        logger.info("No proxy configured")
        return None

    def get_name(self) -> str:
        return "No Proxy"


class ScrapeOpsProvider(ProxyProvider):
    """
    ScrapeOps proxy provider.
    Requires SCRAPEOPS_API_KEY environment variable.
    """

    def get_config(self) -> Optional[Dict[str, str]]:
        if not settings.SCRAPEOPS_API_KEY:
            logger.warning("SCRAPEOPS_API_KEY not found. Cannot use ScrapeOps proxy.")
            return None

        logger.info("Using ScrapeOps Proxy")
        return {
            "server": "http://proxy.scrapeops.io:5353",
            "username": "scrapeops",
            "password": settings.SCRAPEOPS_API_KEY,
        }

    def get_name(self) -> str:
        return "ScrapeOps"


class ScraperAPIProvider(ProxyProvider):
    """
    ScraperAPI proxy provider.
    Requires SCRAPERAPI_API_KEY environment variable.
    """

    def get_config(self) -> Optional[Dict[str, str]]:
        if not settings.SCRAPERAPI_API_KEY:
            logger.warning("SCRAPERAPI_API_KEY not found. Cannot use ScraperAPI proxy.")
            return None

        logger.info("Using ScraperAPI Proxy")
        return {
            "server": "http://proxy-server.scraperapi.com:8001",
            "username": "scraperapi",
            "password": settings.SCRAPERAPI_API_KEY,
        }

    def get_name(self) -> str:
        return "ScraperAPI"


class GenericProxyProvider(ProxyProvider):
    """
    Generic HTTP/SOCKS proxy provider.
    Supports any standard proxy server with optional authentication.
    Requires PROXY_SERVER environment variable.
    Optional: PROXY_USERNAME and PROXY_PASSWORD for authenticated proxies.
    """

    def get_config(self) -> Optional[Dict[str, str]]:
        if not settings.PROXY_SERVER:
            logger.warning("PROXY_SERVER not found. Cannot use generic proxy.")
            return None

        logger.info(f"Using Generic Proxy: {settings.PROXY_SERVER}")
        config = {"server": settings.PROXY_SERVER}

        # Add authentication if provided
        if settings.PROXY_USERNAME:
            config["username"] = settings.PROXY_USERNAME
        if settings.PROXY_PASSWORD:
            config["password"] = settings.PROXY_PASSWORD

        return config

    def get_name(self) -> str:
        return "Generic Proxy"


class ZenRowsProvider(ProxyProvider):
    """
    ZenRows proxy provider.
    Requires ZENROWS_API_KEY environment variable.
    """

    def get_config(self) -> Optional[Dict[str, str]]:
        if not settings.ZENROWS_API_KEY:
            logger.warning("ZENROWS_API_KEY not found. Cannot use ZenRows proxy.")
            return None

        logger.info("Using ZenRows Proxy with anti-bot protection")
        # When using with Playwright, don't use js_render=true (Playwright already does this)
        # Use premium_proxy and antibot for bypassing bot detection
        return {
            "server": "http://api.zenrows.com:8001",
            "username": settings.ZENROWS_API_KEY,
            "password": "premium_proxy=true&antibot=true",
        }

    def get_name(self) -> str:
        return "ZenRows"


# Provider registry: maps provider names to their classes
PROXY_PROVIDERS: Dict[str, type[ProxyProvider]] = {
    "none": NoProxyProvider,
    "scrapeops": ScrapeOpsProvider,
    "scraperapi": ScraperAPIProvider,
    "generic": GenericProxyProvider,
    "zenrows": ZenRowsProvider,
}


def get_proxy_config() -> Optional[Dict[str, str]]:
    """
    Build proxy configuration for the browser context based on PROXY_PROVIDER setting.

    Returns:
        Dict with 'server', 'username', 'password' keys if proxy is configured,
        None otherwise.

    Supported providers (set via PROXY_PROVIDER env var):
        - 'none': No proxy (default)
        - 'scrapeops': ScrapeOps proxy service
        - 'scraperapi': ScraperAPI proxy service
        - 'zenrows': ZenRows proxy service
        - 'generic': Generic HTTP/SOCKS proxy (requires PROXY_SERVER)
    """
    provider_name = settings.PROXY_PROVIDER.lower()

    # Get provider class from registry
    provider_class = PROXY_PROVIDERS.get(provider_name)

    if not provider_class:
        logger.error(
            f"Unknown proxy provider: '{provider_name}'. "
            f"Available providers: {', '.join(PROXY_PROVIDERS.keys())}"
        )
        logger.warning("Falling back to no proxy.")
        return None

    # Instantiate and get configuration
    provider = provider_class()
    return provider.get_config()
