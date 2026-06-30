from __future__ import annotations

from html import unescape
import re
from urllib.parse import quote
from typing import Any

from ..models import Asset, AssetKind
from ..utils.http import build_url, request_json
from .base import AdapterUnavailable, MediaAdapter


class PixabayAdapter(MediaAdapter):
    source_name = "Pixabay"
    supported_kinds = {AssetKind.IMAGE, AssetKind.VIDEO, AssetKind.MUSIC, AssetKind.SFX, AssetKind.MODEL_3D}

    def __init__(self, api_key: str):
        self.api_key = api_key

    def is_available(self) -> bool:
        return True

    def search(self, query: str, kind: AssetKind, *, page: int = 1, per_page: int = 20) -> list[Asset]:
        if not self.api_key and kind in {AssetKind.IMAGE, AssetKind.VIDEO}:
            raise AdapterUnavailable("Pixabay API key is missing.")
        if kind == AssetKind.IMAGE:
            return self._search_images(query, page=page, per_page=per_page)
        if kind == AssetKind.VIDEO:
            return self._search_videos(query, page=page, per_page=per_page)
        if kind == AssetKind.MUSIC:
            return self._search_music_best_effort(query, page=page, per_page=per_page)
        if kind == AssetKind.SFX:
            return self._search_sfx_best_effort(query, page=page, per_page=per_page)
        if kind == AssetKind.MODEL_3D:
            return self._search_3d_best_effort(query, page=page, per_page=per_page)
        return []

    def _search_images(self, query: str, *, page: int, per_page: int) -> list[Asset]:
        per_page = _pixabay_per_page(per_page)
        url = build_url(
            "https://pixabay.com/api/",
            {
                "key": self.api_key,
                "q": query,
                "page": page,
                "per_page": per_page,
                "image_type": "photo",
                "safesearch": "true",
            },
        )
        payload = request_json(url)
        hits = payload.get("hits", []) if isinstance(payload, dict) else []
        return [self._image_to_asset(hit) for hit in hits if isinstance(hit, dict)]

    def _search_videos(self, query: str, *, page: int, per_page: int) -> list[Asset]:
        per_page = _pixabay_per_page(per_page)
        url = build_url(
            "https://pixabay.com/api/videos/",
            {
                "key": self.api_key,
                "q": query,
                "page": page,
                "per_page": per_page,
                "safesearch": "true",
            },
        )
        payload = request_json(url)
        hits = payload.get("hits", []) if isinstance(payload, dict) else []
        return [self._video_to_asset(hit) for hit in hits if isinstance(hit, dict)]

    def _image_to_asset(self, hit: dict[str, Any]) -> Asset:
        tags = _split_tags(hit.get("tags"))
        return Asset(
            id=str(hit.get("id", "")),
            source=self.source_name,
            kind=AssetKind.IMAGE,
            title=", ".join(tags[:3]) or f"Pixabay image {hit.get('id', '')}",
            author=str(hit.get("user", "")),
            author_url=f"https://pixabay.com/users/{hit.get('user', '')}-{hit.get('user_id', '')}/",
            license_name="Pixabay Content License",
            license_url="https://pixabay.com/service/license-summary/",
            source_url=str(hit.get("pageURL", "")),
            preview_url=str(hit.get("webformatURL", "")),
            thumbnail_url=str(hit.get("previewURL", "")),
            download_url=str(hit.get("largeImageURL") or hit.get("webformatURL") or ""),
            width=_int_or_none(hit.get("imageWidth")),
            height=_int_or_none(hit.get("imageHeight")),
            tags=tags,
            metadata={"raw": hit},
        )

    def _video_to_asset(self, hit: dict[str, Any]) -> Asset:
        videos = hit.get("videos", {}) if isinstance(hit.get("videos", {}), dict) else {}
        video_file = _pick_best_pixabay_video(videos)
        tags = _split_tags(hit.get("tags"))
        thumbnail_url = _pixabay_video_thumbnail(video_file, hit.get("picture_id"))
        return Asset(
            id=str(hit.get("id", "")),
            source=self.source_name,
            kind=AssetKind.VIDEO,
            title=", ".join(tags[:3]) or f"Pixabay video {hit.get('id', '')}",
            author=str(hit.get("user", "")),
            author_url=f"https://pixabay.com/users/{hit.get('user', '')}-{hit.get('user_id', '')}/",
            license_name="Pixabay Content License",
            license_url="https://pixabay.com/service/license-summary/",
            source_url=str(hit.get("pageURL", "")),
            preview_url=str(video_file.get("url", "")),
            thumbnail_url=thumbnail_url,
            download_url=str(video_file.get("url", "")),
            duration=_float_or_none(hit.get("duration")),
            width=_int_or_none(video_file.get("width")),
            height=_int_or_none(video_file.get("height")),
            tags=tags,
            metadata={"raw": hit},
        )

    def _search_music_best_effort(self, query: str, *, page: int, per_page: int) -> list[Asset]:
        return _scrape_pixabay_listing(
            source_name=self.source_name,
            kind=AssetKind.MUSIC,
            url=f"https://pixabay.com/music/search/{_slug(query)}/?pagi={page}",
            per_page=per_page,
        )

    def _search_sfx_best_effort(self, query: str, *, page: int, per_page: int) -> list[Asset]:
        return _scrape_pixabay_listing(
            source_name=self.source_name,
            kind=AssetKind.SFX,
            url=f"https://pixabay.com/sound-effects/search/{_slug(query)}/?pagi={page}",
            per_page=per_page,
        )

    def _search_3d_best_effort(self, query: str, *, page: int, per_page: int) -> list[Asset]:
        return _scrape_pixabay_listing(
            source_name=self.source_name,
            kind=AssetKind.MODEL_3D,
            url=f"https://pixabay.com/3d-models/search/{_slug(query)}/?pagi={page}",
            per_page=per_page,
        )


def _scrape_pixabay_listing(source_name: str, kind: AssetKind, url: str, per_page: int) -> list[Asset]:
    from ..utils.http import request_bytes

    try:
        html = request_bytes(url).text
    except RuntimeError as exc:
        if _is_pixabay_cloudflare_block(exc):
            return []
        raise
    anchors = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.IGNORECASE | re.DOTALL)
    assets: list[Asset] = []
    seen: set[str] = set()
    for href, label_html in anchors:
        if len(assets) >= per_page:
            break
        if kind == AssetKind.MUSIC and not href.startswith("/music/"):
            continue
        if kind == AssetKind.SFX and not href.startswith("/sound-effects/"):
            continue
        if kind == AssetKind.MODEL_3D and not href.startswith("/3d-models/"):
            continue
        if href in seen or "/search/" in href:
            continue
        seen.add(href)
        title = _strip_html(label_html).strip()
        if not title or len(title) < 3:
            title = href.rstrip("/").split("/")[-1].replace("-", " ").title()
        source_url = f"https://pixabay.com{href}" if href.startswith("/") else href
        assets.append(
            Asset(
                id=href.strip("/").split("/")[-1],
                source=source_name,
                kind=kind,
                title=title,
                license_name="Pixabay Content License",
                license_url="https://pixabay.com/service/license-summary/",
                source_url=source_url,
                preview_url=source_url,
                download_url="",
                metadata={"scraped": True, "listing_url": url},
            )
        )
    return assets


def _pick_best_pixabay_video(videos: dict[str, Any]) -> dict[str, Any]:
    for key in ("large", "medium", "small", "tiny"):
        item = videos.get(key)
        if isinstance(item, dict) and item.get("url"):
            return item
    return {}


def _pixabay_video_thumbnail(video_file: dict[str, Any], picture_id: object) -> str:
    """Pixabay video hits expose a thumbnail on each rendition; fall back to the
    Vimeo CDN poster derived from picture_id when no direct thumbnail is given."""
    direct = str(video_file.get("thumbnail", "")) if isinstance(video_file, dict) else ""
    if direct:
        return direct
    pid = str(picture_id or "").strip()
    if pid:
        return f"https://i.vimeocdn.com/video/{pid}_295x166.jpg"
    return ""


def _split_tags(value: object) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in str(value).split(",") if part.strip()]


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


def _slug(value: str) -> str:
    return quote(value.strip())


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = re.sub(r"\s+", " ", text)
    return unescape(text)


def _is_pixabay_cloudflare_block(error: Exception) -> bool:
    message = str(error).lower()
    return "http 403" in message and "just a moment" in message


def _pixabay_per_page(value: int) -> int:
    return max(3, min(200, value))
