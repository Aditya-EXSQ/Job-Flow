import asyncio
import logging
from scraper.core.browser import BrowserManager

# Configure logging
logging.basicConfig(level=logging.INFO)


async def main():
    print("Initializing BrowserManager...")
    await BrowserManager.initialize()

    context = await BrowserManager.get_context()
    page = await BrowserManager.new_page()

    # Check User Agent via Playwright
    ua = await page.evaluate("navigator.userAgent")
    print(f"Verified User Agent: {ua}")

    # Check viewport
    viewport = page.viewport_size
    print(f"Verified Viewport: {viewport}")

    await BrowserManager.close()
    print("Browser closed.")


if __name__ == "__main__":
    asyncio.run(main())
