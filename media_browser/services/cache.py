from __future__ import annotations

import hashlib
import json
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

from ..models import Asset


class CacheManager:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.media_dir = cache_dir / "media"
        self.meta_dir = cache_dir / "metadata"
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def media_path_for(self, asset: Asset, url: str | None = None) -> Path:
        download_url = url or asset.download_url or asset.preview_url or asset.source_url
        digest = hashlib.sha256(f"{asset.source}:{asset.id}:{download_url}".encode("utf-8")).hexdigest()[:24]
        extension = _safe_extension(_extension_from_url(download_url) or _extension_from_kind(asset.kind))
        safe_source = _safe_token(asset.source.lower())
        safe_id = _safe_token(asset.id)
        return self.media_dir / f"{safe_source}_{safe_id}_{digest}{extension}"

    def metadata_path_for(self, asset: Asset) -> Path:
        digest = hashlib.sha256(f"{asset.source}:{asset.id}".encode("utf-8")).hexdigest()[:24]
        safe_source = _safe_token(asset.source.lower())
        safe_id = _safe_token(asset.id)
        return self.meta_dir / f"{safe_source}_{safe_id}_{digest}.json"

    def has_media(self, asset: Asset) -> bool:
        return self.media_path_for(asset).exists()

    def write_metadata(self, asset: Asset, media_path: Path) -> Path:
        payload = asset.to_dict()
        payload["local_media_path"] = str(media_path)
        metadata_path = self.metadata_path_for(asset)
        with metadata_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        return metadata_path


def _safe_token(value: str) -> str:
    """Keep only filename-safe characters so a hostile id/source can't traverse
    out of the cache directory (uniqueness still comes from the sha256 digest)."""
    cleaned = "".join(ch for ch in str(value) if ch.isalnum() or ch in ("-", "_"))
    return cleaned[:48] or "item"


def _safe_extension(extension: str) -> str:
    if not extension:
        return ""
    cleaned = "." + "".join(ch for ch in extension.lstrip(".") if ch.isalnum())
    return cleaned[:10] if len(cleaned) > 1 else ""


def _extension_from_url(url: str) -> str:
    path = urlparse(url).path
    suffix = Path(path).suffix
    if suffix and len(suffix) <= 8:
        return suffix
    guessed, _ = mimetypes.guess_type(url)
    if guessed:
        extension = mimetypes.guess_extension(guessed)
        if extension:
            return extension
    return ""


def _extension_from_kind(kind: object) -> str:
    value = str(kind)
    if value == "image":
        return ".jpg"
    if value == "video":
        return ".mp4"
    if value in {"music", "sfx"}:
        return ".mp3"
    if value == "3d":
        return ".glb"
    return ".bin"
