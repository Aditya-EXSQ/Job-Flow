import asyncio
import logging
import random
import os
from typing import Optional, AsyncGenerator
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)
from scraper.config.settings import settings

from fake_useragent import UserAgent

logger = logging.getLogger(__name__)


class BrowserManager:
    """
    Manages the lifecycle of the Playwright browser and context.
    """

    _playwright: Optional[Playwright] = None
    _browser: Optional[Browser] = None
    _context: Optional[BrowserContext] = None
    _ua: Optional[UserAgent] = None

    @classmethod
    async def initialize(cls):
        """
        Initializes the browser and context if not already running.
        """
        if cls._ua is None:
            try:
                # Initialize UserAgent with a fallback to prevent hanging/errors
                cls._ua = UserAgent(
                    browsers=["chrome", "firefox", "safari"],
                    os=["windows", "macos"],
                    fallback="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                )
            except Exception as e:
                logger.warning(
                    f"Failed to initialize fake_useragent, using fallback: {e}"
                )
                # Create a dummy object or handle fallback manually if UserAgent fails completely
                # But UserAgent should handle fallback.
                # If it still hangs, we might need to run it in a thread or disable external data.
                pass

        if cls._playwright is None:
            cls._playwright = await async_playwright().start()
            logger.info("Playwright started.")

        if cls._browser is None:
            # Enhanced browser arguments to avoid detection
            launch_args = [
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
            
            cls._browser = await cls._playwright.chromium.launch(
                headless=settings.HEADLESS,
                args=launch_args,
            )
            logger.info(f"Browser launched (Headless: {settings.HEADLESS}).")

        if cls._context is None:
            # Generate a random user agent
            if cls._ua:
                user_agent = cls._ua.random
            else:
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            logger.info(f"Using User Agent: {user_agent}")

            # Proxy configuration
            proxy_config = None
            if settings.SCRAPEOPS_API_KEY:
                logger.info("Using ScrapeOps Proxy")
                proxy_config = {
                    "server": "http://proxy.scrapeops.io:5353",
                    "username": "scrapeops",
                    "password": settings.SCRAPEOPS_API_KEY,
                }
            else:
                logger.warning("SCRAPEOPS_API_KEY not found. No proxy will be used.")

            cls._context = await cls._browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1366, "height": 768},
                locale="en-US",
                timezone_id="America/New_York",
                proxy=proxy_config,
                ignore_https_errors=settings.IGNORE_HTTPS_ERRORS,
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0',
                },
            )

            # Enhanced stealth: Override multiple navigator properties to avoid detection
            platform = "Win32" if "Windows" in user_agent else "MacIntel" if "Mac" in user_agent else "Linux x86_64"
            await cls._context.add_init_script(f"""
                // Override navigator properties
                Object.defineProperty(navigator, 'platform', {{
                    get: () => '{platform}'
                }});
                
                // Hide webdriver property
                Object.defineProperty(navigator, 'webdriver', {{
                    get: () => undefined
                }});
                
                // Remove automation flags
                delete navigator.__proto__.webdriver;
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({{ state: Notification.permission }}) :
                        originalQuery(parameters)
                );
                
                // Plugin spoofing
                Object.defineProperty(navigator, 'plugins', {{
                    get: () => [
                        {{
                            0: {{type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"}},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Plugin"
                        }},
                        {{
                            0: {{type: "application/pdf", suffixes: "pdf", description: ""}},
                            description: "",
                            filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                            length: 1,
                            name: "Chrome PDF Viewer"
                        }},
                        {{
                            0: {{type: "application/x-nacl", suffixes: "", description: "Native Client Executable"}},
                            description: "Native Client Executable",
                            filename: "internal-nacl-plugin",
                            length: 2,
                            name: "Native Client"
                        }}
                    ]
                }});
                
                // Languages
                Object.defineProperty(navigator, 'languages', {{
                    get: () => ['en-US', 'en']
                }});
                
                // Chrome runtime
                window.chrome = {{
                    runtime: {{}}
                }};
                
                // Screen properties
                Object.defineProperty(window.screen, 'availWidth', {{
                    get: () => 1366
                }});
                Object.defineProperty(window.screen, 'availHeight', {{
                    get: () => 768
                }});
            """)

            logger.info("Browser context created with stealth settings.")

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
        page = await context.new_page()
        return page

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
