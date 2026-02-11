import asyncio
import logging
import sys
from scraper.core.runner import runner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


async def main():
    """
    Main entry point.
    """
    # Example usage: Could be replaced by CLI arguments parser (e.g., typer or argparse)
    portal = "indeed"
    query = "python developer"
    location = "Remote"

    await runner.run(portal=portal, query=query, location=location)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
