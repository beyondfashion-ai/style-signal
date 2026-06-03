from .sources.base import SourceAdapter
from .sources.farfetch.adapter import FarfetchAdapter
from .sources.grailed.adapter import GrailedAdapter
from .sources.kream.adapter import KreamAdapter
from .sources.musinsa.adapter import MusinsaAdapter
from .sources.ssense.adapter import SsenseAdapter
from .sources.styleshare.adapter import StyleshareAdapter
from .sources.twentyninecm.adapter import TwentyNineCMAdapter


_ADAPTERS: dict[str, type[SourceAdapter]] = {
    "kream": KreamAdapter,
    "musinsa": MusinsaAdapter,
    "29cm": TwentyNineCMAdapter,
    "ssense": SsenseAdapter,
    "farfetch": FarfetchAdapter,
    "grailed": GrailedAdapter,
    "styleshare": StyleshareAdapter,
}


def get_adapter(name: str) -> SourceAdapter:
    if name not in _ADAPTERS:
        available = ", ".join(list_sources())
        raise ValueError(f"Unknown source: {name}. Available: {available}")
    return _ADAPTERS[name]()


def list_sources() -> list[str]:
    return sorted(_ADAPTERS.keys())
