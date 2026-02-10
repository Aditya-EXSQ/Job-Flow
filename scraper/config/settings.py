import os
from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    """
    Configuration settings for the scraper.
    """

    # Browser settings
    HEADLESS: bool = False
    BROWSER_TYPE: str = "chromium"  # chromium, firefox, webkit
    # Some proxy networks and certain environments can cause TLS verification failures
    # (e.g., net::ERR_CERT_AUTHORITY_INVALID). For scraping, it's often acceptable to
    # ignore these errors to keep navigation resilient.
    IGNORE_HTTPS_ERRORS: bool = True

    # Rate limiting & Concurrency
    MAX_CONCURRENT_PAGES: int = 5
    MAX_CONCURRENT_SERP: int = 1

    # Retries
    MAX_RETRIES: int = 3
    RETRY_BASE_DELAY: float = 5.0  # seconds
    RETRY_MAX_DELAY: float = 10.0  # seconds

    # Timeouts
    NAVIGATION_TIMEOUT: int = 30000  # ms
    SELECTOR_TIMEOUT: int = 10000  # ms

    # Proxies
    SCRAPEOPS_API_KEY: str = os.getenv("SCRAPEOPS_API_KEY")

settings = Settings()
