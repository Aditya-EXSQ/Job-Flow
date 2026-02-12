"""
Pagination logic for Indeed SERP navigation.
"""

import urllib.parse
from scraper.adapters.indeed.config import SEARCH_URL


def build_serp_url(query: str, location: str, page_num: int, jobs_per_page: int) -> str:
    """
    Build an Indeed search results URL for a given page number.
    """
    start_offset = page_num * jobs_per_page
    params = {
        "q": query,
        "l": location,
        "sort": "date",
        "start": start_offset,
    }
    return f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"
