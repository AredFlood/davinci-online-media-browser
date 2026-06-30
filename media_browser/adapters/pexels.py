from __future__ import annotations

from typing import Any

from ..models import Asset, AssetKind
from ..utils.http import build_url, request_json
from .base import AdapterUnavailable, MediaAdapter


class PexelsAdapter(MediaAdapter):
    source_name = "Pexels"
    supported_kinds = {AssetKind.IMAGE, AssetKind.VIDEO}

    def __init__(self, api_key: str):
        self.api_key = api_key

    def is_available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, kind: AssetKind, *, page: int = 1, per_page: int = 20) -> list[Asset]:
        if not self.api_key:
            raise AdapterUnavailable("Pexels API key is missing.")
        if kind == AssetKind.IMAGE:
            return self._search_photos(query, page=page, per_page=per_page)
        if kind == AssetKind.VIDEO:
            return self._search_videos(query, page=page, per_page=per_page)
        return []

    def _headers(self) -> dict[str, str]:
        return {"Authorization": self.api_key}

    def _search_photos(self, query: str, *, page: int, per_page: int) -> list[Asset]:
        url = build_url(
            "https://api.pexels.com/v1/search",
            {"query": query, "page": page, "per_page": per_page, "locale": "en-US"},
        )
        payload = request_json(url, headers=self._headers())
        photos = payload.get("photos", []) if isinstance(payload, dict) else []
        return [self._photo_to_asset(photo) for photo in photos if isinstance(photo, dict)]

    def _search_videos(self, query: str, *, page: int, per_page: int) -> list[Asset]:
        url = build_url(
            "https://api.pexels.com/videos/search",
            {"query": query, "page": page, "per_page": per_page, "orientation": None},
        )
        payload = request_json(url, headers=self._headers())
        videos = payload.get("videos", []) if isinstance(payload, dict) else []
        return [self._video_to_asset(video) for video in videos if isinstance(video, dict)]

    def _photo_to_asset(self, photo: dict[str, Any]) -> Asset:
        src = photo.get("src", {}) if isinstance(photo.get("src", {}), dict) else {}
        return Asset(
            id=str(photo.get("id", "")),
            source=self.source_name,
            kind=AssetKind.IMAGE,
            title=str(photo.get("alt") or f"Pexels photo {photo.get('id', '')}"),
            author=str(photo.get("photographer", "")),
            author_url=str(photo.get("photographer_url", "")),
            license_name="Pexels License",
            license_url="https://www.pexels.com/license/",
            source_url=str(photo.get("url", "")),
            preview_url=str(src.get("large2x") or src.get("large") or src.get("medium") or ""),
            thumbnail_url=str(src.get("medium") or src.get("small") or ""),
            download_url=str(src.get("original") or src.get("large2x") or ""),
            width=_int_or_none(photo.get("width")),
            height=_int_or_none(photo.get("height")),
            tags=[query_part for query_part in str(photo.get("alt", "")).lower().split()[:10]],
            metadata={"raw": photo},
        )

    def _video_to_asset(self, video: dict[str, Any]) -> Asset:
        video_file = _pick_best_pexels_video(video.get("video_files", []))
        pictures = video.get("video_pictures", [])
        thumbnail_url = ""
        if isinstance(pictures, list) and pictures:
            first_picture = pictures[0]
            if isinstance(first_picture, dict):
                thumbnail_url = str(first_picture.get("picture", ""))
        user = video.get("user", {}) if isinstance(video.get("user", {}), dict) else {}
        return Asset(
            id=str(video.get("id", "")),
            source=self.source_name,
            kind=AssetKind.VIDEO,
            title=f"Pexels video {video.get('id', '')}",
            author=str(user.get("name", "")),
            author_url=str(user.get("url", "")),
            license_name="Pexels License",
            license_url="https://www.pexels.com/license/",
            source_url=str(video.get("url", "")),
            preview_url=str(video_file.get("link", "")),
            thumbnail_url=thumbnail_url,
            download_url=str(video_file.get("link", "")),
            duration=_float_or_none(video.get("duration")),
            width=_int_or_none(video.get("width")),
            height=_int_or_none(video.get("height")),
            tags=[],
            metadata={"raw": video},
        )


def _pick_best_pexels_video(video_files: object) -> dict[str, Any]:
    if not isinstance(video_files, list):
        return {}
    candidates = [item for item in video_files if isinstance(item, dict) and item.get("link")]
    if not candidates:
        return {}
    mp4_candidates = [item for item in candidates if str(item.get("file_type", "")).lower() == "video/mp4"]
    candidates = mp4_candidates or candidates
    return max(candidates, key=lambda item: int(item.get("width") or 0) * int(item.get("height") or 0))


def _int_or_none(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _float_or_none(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
