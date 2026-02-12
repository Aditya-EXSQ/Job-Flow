"""
Human-like mouse movement and keyboard input for Playwright pages.

Provides Bézier-curve cursor paths, smooth mouse traversal, and
character-by-character typing with random cadence — all aimed at
making automated interactions indistinguishable from a real user.
"""

import logging
import random
from typing import List, Tuple

from playwright.async_api import Page

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cursor-path generation
# ---------------------------------------------------------------------------


def _bezier_point(
    t: float,
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
) -> Tuple[float, float]:
    """Evaluate a cubic Bézier curve at parameter *t* ∈ [0, 1]."""
    u = 1 - t
    x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
    y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
    return (x, y)


def random_cursor_path(
    start: Tuple[float, float],
    end: Tuple[float, float],
    steps: int = 25,
) -> List[Tuple[float, float]]:
    """
    Generate a natural-looking path between *start* and *end* using a
    cubic Bézier curve with two randomly-offset control points.

    Returns a list of ``(x, y)`` waypoints (length = *steps* + 1).
    """
    dx = end[0] - start[0]
    dy = end[1] - start[1]

    # Control points spread randomly around the straight line
    cp1 = (
        start[0] + dx * random.uniform(0.2, 0.4) + random.uniform(-80, 80),
        start[1] + dy * random.uniform(0.2, 0.4) + random.uniform(-80, 80),
    )
    cp2 = (
        start[0] + dx * random.uniform(0.6, 0.8) + random.uniform(-80, 80),
        start[1] + dy * random.uniform(0.6, 0.8) + random.uniform(-80, 80),
    )

    return [_bezier_point(i / steps, start, cp1, cp2, end) for i in range(steps + 1)]


# ---------------------------------------------------------------------------
# Mouse movement
# ---------------------------------------------------------------------------


def _random_viewport_point(width: int, height: int) -> Tuple[float, float]:
    """Return a random point inside the viewport, avoiding extreme edges."""
    margin = 50
    return (
        random.uniform(margin, width - margin),
        random.uniform(margin, height - margin),
    )


async def _element_center(page: Page, selector: str) -> Tuple[float, float]:
    """Return the center ``(x, y)`` of the first element matching *selector*."""
    box = await page.locator(selector).first.bounding_box()
    if box is None:
        raise ValueError(f"Element '{selector}' has no bounding box (not visible?)")
    return (box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


async def move_cursor_to_element(page: Page, selector: str) -> None:
    """
    Spawn the cursor at a random viewport position, then glide it to the
    target element following a Bézier-curved random path and click.

    Each waypoint move has a small random delay to mimic human hand jitter.
    """
    viewport = page.viewport_size or {"width": 1366, "height": 768}
    start = _random_viewport_point(viewport["width"], viewport["height"])
    end = await _element_center(page, selector)

    path = random_cursor_path(start, end, steps=random.randint(20, 35))

    logger.debug(
        "Moving cursor from (%.0f, %.0f) → element '%s' at (%.0f, %.0f)",
        start[0],
        start[1],
        selector,
        end[0],
        end[1],
    )

    for x, y in path:
        await page.mouse.move(x, y)
        await page.wait_for_timeout(random.randint(5, 25))

    # Click once we've reached the target
    await page.mouse.click(end[0], end[1])
    logger.debug("Clicked element '%s'", selector)


# ---------------------------------------------------------------------------
# Keyboard input
# ---------------------------------------------------------------------------


async def human_type(page: Page, selector: str, text: str) -> None:
    """
    Clear any pre-filled value in the input identified by *selector*,
    then type *text* character-by-character with random inter-key delays.

    Assumes the element is already focused (e.g. after ``move_cursor_to_element``).
    """
    # Select-all and delete to clear existing content (works cross-platform)
    await page.locator(selector).first.click(click_count=3)
    await page.wait_for_timeout(random.randint(50, 150))
    await page.keyboard.press("Backspace")
    await page.wait_for_timeout(random.randint(100, 300))

    logger.debug("Typing '%s' into '%s' character-by-character", text, selector)

    for char in text:
        await page.keyboard.type(char)
        await page.wait_for_timeout(random.randint(50, 250))
