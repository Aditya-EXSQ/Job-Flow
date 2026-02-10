"""
Salary extraction from JSON-LD structured data and regex pattern matching.
"""

import logging
import re
from typing import Optional, Dict
from playwright.async_api import Page

from scraper.adapters.indeed.selectors import SALARY_PATTERNS

logger = logging.getLogger(__name__)


async def extract_salary(page: Page, json_ld: Optional[Dict] = None) -> Optional[str]:
    """Extract salary from JSON-LD or text pattern matching"""
    if json_ld and "baseSalary" in json_ld:
        salary = json_ld["baseSalary"]
        if isinstance(salary, dict):
            value = salary.get("value", {})
            if isinstance(value, dict):
                min_val = value.get("minValue")
                max_val = value.get("maxValue")
                currency = value.get("currency", "")
                if min_val and max_val:
                    return f"{currency}{min_val} - {currency}{max_val}"

    # Pattern match for salary text (e.g., "$50,000 - $80,000" or "₹20,000 - ₹30,000")
    try:
        html = await page.content()
        # Match currency symbols followed by numbers
        for pattern in SALARY_PATTERNS:
            match = re.search(pattern, html)
            if match:
                return match.group(0)
    except Exception as e:
        logger.debug(f"Salary pattern matching failed: {e}")

    return None
