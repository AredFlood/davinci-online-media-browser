from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Asset, AssetKind


class AdapterUnavailable(RuntimeError):
    """Raised when an adapter cannot run because credentials or dependencies are missing."""


class MediaAdapter(ABC):
    source_name: str
    supported_kinds: set[AssetKind]

    def is_available(self) -> bool:
        return True

    @abstractmethod
    def search(self, query: str, kind: AssetKind, *, page: int = 1, per_page: int = 20) -> list[Asset]:
        raise NotImplementedError
