"""
Backward-compatibility shim.

The browser management code has been moved to scraper.browser.manager.
This module re-exports BrowserManager and get_browser_context so that
existing imports continue to work.
"""

from scraper.browser.manager import BrowserManager, get_browser_context

__all__ = ["BrowserManager", "get_browser_context"]
