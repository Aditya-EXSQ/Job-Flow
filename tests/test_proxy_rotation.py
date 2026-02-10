import asyncio
import logging
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

print("Importing BrowserManager...")
from scraper.core.browser import BrowserManager

print("BrowserManager imported.")

# Configure logging
logging.basicConfig(level=logging.INFO)


async def check_ip():
    print("Initializing BrowserManager...")
    print("Calling BrowserManager.initialize()...")
    await BrowserManager.initialize()
    print("BrowserManager initialized.")

    print("Getting context...")
    context = await BrowserManager.get_context()
    print("Context obtained.")

    print("Creating new page...")
    page = await BrowserManager.new_page()
    print("Page created.")

    try:
        print("Navigating to IP check service...")
        # Use a timeout to avoid hanging if a proxy is dead
        await page.goto("https://api.ipify.org?format=json", timeout=10000)
        content = await page.content()
        print(f"Page Content: {content}")
        ip = await page.evaluate("() => JSON.parse(document.body.innerText).ip")
        print(f"Current IP: {ip}")
    except Exception as e:
        print(f"Failed to check IP: {e}")
    finally:
        await BrowserManager.close()
        print("Browser closed.")


async def main():
    print("--- Attempt 1 ---")
    await check_ip()
    print("\n--- Attempt 2 ---")
    await check_ip()
    print("\n--- Attempt 3 ---")
    await check_ip()


if __name__ == "__main__":
    asyncio.run(main())
