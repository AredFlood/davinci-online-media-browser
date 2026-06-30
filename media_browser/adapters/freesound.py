from __future__ import annotations

from typing import Any

from ..models import Asset, AssetKind
from ..utils.http import build_url, request_json
from .base import AdapterUnavailable, MediaAdapter


class FreesoundAdapter(MediaAdapter):
    source_name = "Freesound"
    supported_kinds = {AssetKind.SFX}

    def __init__(self, api_key: str, oauth_access_token: str = ""):
        self.api_key = api_key
        self.oauth_access_token = oauth_access_token

    def is_available(self) -> bool:
        return bool(self.api_key or self.oauth_access_token)

    def search(self, query: str, kind: AssetKind, *, page: int = 1, per_page: int = 20) -> list[Asset]:
        if kind != AssetKind.SFX:
            return []
        if not self.is_available():
            raise AdapterUnavailable("Freesound API key or OAuth token is missing.")
        url = build_url(
            "https://freesound.org/apiv2/search/text/",
            {
                "query": query,
                "page": page,
                "page_size": per_page,
                "fields": "id,name,username,url,previews,license,tags,duration,description",
            },
        )
        payload = request_json(url, headers=self._headers())
        results = payload.get("results", []) if isinstance(payload, dict) else []
        return [self._sound_to_asset(item) for item in results if isinstance(item, dict)]

    def _headers(self) -> dict[str, str]:
        if self.oauth_access_token:
            return {"Authorization": f"Bearer {self.oauth_access_token}"}
        return {"Authorization": f"Token {self.api_key}"}

    def _sound_to_asset(self, item: dict[str, Any]) -> Asset:
        previews = item.get("previews", {}) if isinstance(item.get("previews", {}), dict) else {}
        preview_url = str(
            previews.get("preview-hq-mp3")
            or previews.get("preview-lq-mp3")
            or previews.get("preview-hq-ogg")
            or ""
        )
        license_url = str(item.get("license", ""))
        license_name = _license_name_from_url(license_url)
        tags = [str(tag) for tag in item.get("tags", []) if tag] if isinstance(item.get("tags"), list) else []
        return Asset(
            id=str(item.get("id", "")),
            source=self.source_name,
            kind=AssetKind.SFX,
            title=str(item.get("name", "")),
            author=str(item.get("username", "")),
            author_url=f"https://freesound.org/people/{item.get('username', '')}/",
            license_name=license_name,
            license_url=license_url,
            source_url=str(item.get("url", "")),
            preview_url=preview_url,
            thumbnail_url="",
            download_url=preview_url,
            duration=_float_or_none(item.get("duration")),
            tags=tags,
            metadata={
                "raw": item,
                "download_note": "Freesound full-quality downloads require OAuth; preview MP3 is used by default.",
            },
        )


def _license_name_from_url(url: str) -> str:
    normalized = url.lower()
    if "zero" in normalized or "publicdomain/zero" in normalized:
        return "CC0"
    if "by-nc" in normalized:
        return "CC-BY-NC"
    if "/by/" in normalized:
        return "CC-BY"
    return "Creative Commons"


def _float_or_none(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
