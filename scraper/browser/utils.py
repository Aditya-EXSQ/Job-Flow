"""
Browser Utility Functions

Lightweight helpers for adding behavioral realism to scraping.
"""

import asyncio
import random
from typing import Optional


async def random_delay(
    min_seconds: float = 0.5,
    max_seconds: float = 2.0,
    variance: Optional[float] = None,
) -> None:
    """
    Add a randomized delay to mimic human behavior.

    Use between page actions (clicks, form fills, navigations) to avoid
    perfectly timed bot patterns.

    Args:
        min_seconds: Minimum delay in seconds
        max_seconds: Maximum delay in seconds
        variance: Optional additional random variance to add

    Example:
        await random_delay(1.0, 3.0)  # Wait 1-3 seconds
        await page.click('#submit')
    """
    delay = random.uniform(min_seconds, max_seconds)

    if variance:
        delay += random.uniform(-variance, variance)

    # Ensure non-negative
    delay = max(0, delay)

    await asyncio.sleep(delay)
