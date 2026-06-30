from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class AssetKind(StrEnum):
    VIDEO = "video"
    IMAGE = "image"
    MUSIC = "music"
    SFX = "sfx"
    MODEL_3D = "3d"
    TEMPLATE = "template"


@dataclass(slots=True)
class Asset:
    id: str
    source: str
    kind: AssetKind
    title: str
    author: str = ""
    author_url: str = ""
    license_name: str = ""
    license_url: str = ""
    source_url: str = ""
    preview_url: str = ""
    thumbnail_url: str = ""
    download_url: str = ""
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def display_title(self) -> str:
        return self.title or f"{self.source}:{self.id}"

    @property
    def requires_attribution(self) -> bool:
        normalized = self.license_name.lower()
        return "by" in normalized and "cc0" not in normalized

    @property
    def is_non_commercial(self) -> bool:
        normalized = self.license_name.lower()
        return "noncommercial" in normalized or "non-commercial" in normalized or "by-nc" in normalized

    @property
    def is_attribution_free(self) -> bool:
        """True when the asset can be used commercially without crediting the author."""
        return not self.requires_attribution and not self.is_non_commercial

    @property
    def license_badge(self) -> str:
        """Short label for thumbnail overlays, e.g. NC / BY / CC0 / ©."""
        normalized = self.license_name.lower()
        if self.is_non_commercial:
            return "NC"
        if "cc0" in normalized or "zero" in normalized or "public domain" in normalized:
            return "CC0"
        if self.requires_attribution:
            return "BY"
        if normalized:
            return "©"
        return ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = str(self.kind)
        return data


@dataclass(slots=True)
class SearchError:
    source: str
    message: str
