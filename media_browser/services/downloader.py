from __future__ import annotations

from pathlib import Path

from ..models import Asset
from ..utils.http import CancelCheck, DownloadCancelled, ProgressCallback, download_to_file
from .cache import CacheManager


class DownloadError(RuntimeError):
    pass


# Re-exported so UI/worker code can catch cancellation without reaching into utils.
__all__ = ["DownloadError", "DownloadCancelled", "Downloader"]


class Downloader:
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager

    def download(
        self,
        asset: Asset,
        *,
        progress: ProgressCallback | None = None,
        cancel: CancelCheck | None = None,
    ) -> Path:
        url = asset.download_url or asset.preview_url
        if not url or url == asset.source_url:
            raise DownloadError(
                f"{asset.source} item '{asset.display_title}' has no direct downloadable URL. Open the source page instead."
            )
        media_path = self.cache_manager.media_path_for(asset, url)
        if media_path.exists() and media_path.stat().st_size > 0:
            self.cache_manager.write_metadata(asset, media_path)
            if progress:
                size = media_path.stat().st_size
                progress(size, size)
            return media_path
        written = download_to_file(url, media_path, timeout=120.0, progress=progress, cancel=cancel)
        if written <= 0:
            media_path.unlink(missing_ok=True)
            raise DownloadError(f"Download returned an empty file: {url}")
        self.cache_manager.write_metadata(asset, media_path)
        return media_path
