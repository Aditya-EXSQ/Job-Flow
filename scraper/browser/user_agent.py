import logging
from typing import Optional

from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

# Default fallback user agent string
FALLBACK_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36"
)


class UserAgentProvider:
    """
    Manages fake user-agent generation and rotation.
    """

    _ua: Optional[UserAgent] = None

    @classmethod
    def initialize(cls):
        """
        Initialize the UserAgent provider if not already done.
        """
        if cls._ua is None:
            try:
                # Initialize UserAgent with a fallback to prevent hanging/errors
                cls._ua = UserAgent(
                    browsers=["chrome", "firefox", "safari"],
                    os=["windows", "macos"],
                    fallback=FALLBACK_UA,
                )
            except Exception as e:
                logger.warning(
                    f"Failed to initialize fake_useragent, using fallback: {e}"
                )
                # Create a dummy object or handle fallback manually if UserAgent fails completely
                # But UserAgent should handle fallback.
                # If it still hangs, we might need to run it in a thread or disable external data.
                pass

    @classmethod
    def get_random(cls) -> str:
        """
        Return a random user-agent string, or the fallback if not initialized.
        """
        if cls._ua:
            return cls._ua.random
        return FALLBACK_UA
