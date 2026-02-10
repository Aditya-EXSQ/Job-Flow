from dataclasses import dataclass
from typing import Optional


@dataclass
class Job:
    """
    Canonical Job model representing a standardized job posting.
    """

    id: str
    title: str
    company: str
    location: str
    description: str
    source: str
    url: str
    salary: Optional[str] = None
    posted_at: Optional[str] = None
