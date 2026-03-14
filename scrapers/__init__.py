from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class FeedItem:
    title: str
    url: str
    description: str = ""
    published: Optional[datetime] = None
    source: str = ""
    extra: dict = field(default_factory=dict)  # university, country, deadline, etc.


class BaseSource(ABC):
    name: str = ""

    @abstractmethod
    async def fetch(self) -> List[FeedItem]:
        """Scrape and return a list of FeedItems."""
        ...
