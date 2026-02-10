import asyncio
import random
import logging
import functools
from typing import Callable, Any, TypeVar, Coroutine
from playwright.async_api import Error as PlaywrightError
from scraper.config.settings import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RateLimiter:
    """
    Manages concurrency using asyncio.Semaphore.
    """

    def __init__(self, max_concurrent: int):
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def acquire(self):
        await self._semaphore.acquire()

    def release(self):
        self._semaphore.release()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()


# Global rate limiters
page_limiter = RateLimiter(settings.MAX_CONCURRENT_PAGES)
serp_limiter = RateLimiter(settings.MAX_CONCURRENT_SERP)


def with_retry(
    max_retries: int = settings.MAX_RETRIES,
    base_delay: float = settings.RETRY_BASE_DELAY,
    max_delay: float = settings.RETRY_MAX_DELAY,
):
    """
    Decorator for async functions to retry on failure with exponential backoff and jitter.
    """

    def decorator(
        func: Callable[..., Coroutine[Any, Any, T]],
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            retries = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except (PlaywrightError, asyncio.TimeoutError) as e:
                    if retries >= max_retries:
                        logger.error(
                            f"Max retries reached for {func.__name__}. Error: {e}"
                        )
                        raise

                    delay = min(base_delay * (2**retries), max_delay)
                    jitter = random.uniform(0, 0.5 * delay)
                    sleep_time = delay + jitter

                    logger.warning(
                        f"Attempt {retries + 1}/{max_retries} failed for {func.__name__}. "
                        f"Retrying in {sleep_time:.2f}s. Error: {e}"
                    )

                    await asyncio.sleep(sleep_time)
                    retries += 1
                except Exception as e:
                    # Non-retryable exceptions
                    logger.exception(f"Unhandled exception in {func.__name__}: {e}")
                    raise

        return wrapper

    return decorator
