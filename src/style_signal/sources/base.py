from abc import ABC, abstractmethod
from typing import Optional

from ..schema import Product, Query


class SourceAdapter(ABC):
    name: str
    status: str = "ready"
    supported_genders: tuple[str, ...] = ("men", "women", "unisex")
    supported_sorts: tuple[str, ...] = ("popular",)
    supported_categories: dict[str, str] = {}
    supported_curations: tuple[str, ...] = ()

    @abstractmethod
    def build_url(self, query: Query) -> str:
        raise NotImplementedError

    @abstractmethod
    def parse(self, raw_markdown: str, query: Query) -> list[Product]:
        raise NotImplementedError

    def detect_block(self, raw_markdown: str, file_size: int) -> Optional[str]:
        if file_size < 1000:
            lowered = raw_markdown.lower()
            if any(sig in lowered for sig in ("akamai", "blocked", "access denied", "bot detect")):
                return "BLOCKED"
            return "EMPTY_RESULT"
        return None

    def describe(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "supported_categories": self.supported_categories,
            "supported_genders": list(self.supported_genders),
            "supported_sorts": list(self.supported_sorts),
            "supported_curations": list(self.supported_curations),
        }
