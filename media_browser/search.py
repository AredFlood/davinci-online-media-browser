from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from .adapters import FreesoundAdapter, MediaAdapter, MixkitAdapter, PexelsAdapter, PixabayAdapter
from .config import AppConfig
from .models import Asset, AssetKind, SearchError


VISUAL_WORDS = {"video", "footage", "clip", "视频", "素材", "b-roll", "broll"}
IMAGE_WORDS = {"image", "photo", "picture", "图片", "照片", "图像"}
MUSIC_WORDS = {"music", "bgm", "song", "track", "音乐", "配乐", "背景音乐"}
SFX_WORDS = {"sfx", "sound effect", "sound", "whoosh", "hit", "音效", "声音", "拟音"}


@dataclass(slots=True)
class SearchResult:
    assets: list[Asset]
    errors: list[SearchError]


class SearchRouter:
    def __init__(self, adapters: list[MediaAdapter]):
        self.adapters = adapters
        self.last_errors: list[SearchError] = []

    @classmethod
    def from_config(cls, config: AppConfig) -> "SearchRouter":
        adapters: list[MediaAdapter] = [
            PexelsAdapter(config.pexels_api_key),
            PixabayAdapter(config.pixabay_api_key),
            FreesoundAdapter(config.freesound_api_key, oauth_access_token=config.freesound_oauth_access_token),
            MixkitAdapter(enabled=config.mixkit_enabled),
        ]
        return cls(adapters)

    def search(self, query: str, *, category: str = "all", page: int = 1, per_page: int = 20) -> list[Asset]:
        result = self.search_with_errors(query, category=category, page=page, per_page=per_page)
        self.last_errors = result.errors
        return result.assets

    def search_with_errors(self, query: str, *, category: str = "all", page: int = 1, per_page: int = 20) -> SearchResult:
        kinds = self._route_kinds(query, category)
        tasks: list[tuple[int, MediaAdapter, AssetKind]] = []
        early_errors: list[SearchError] = []
        for kind in kinds:
            for adapter in self.adapters:
                if kind not in adapter.supported_kinds:
                    continue
                if not adapter.is_available():
                    early_errors.append(SearchError(adapter.source_name, "Adapter not configured."))
                    continue
                tasks.append((len(tasks), adapter, kind))

        assets: list[Asset] = []
        errors: list[SearchError] = list(early_errors)
        if not tasks:
            return SearchResult(assets=[], errors=errors)

        results: dict[int, list[Asset]] = {}
        task_errors: dict[int, SearchError] = {}
        max_workers = min(8, len(tasks))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(adapter.search, query, kind, page=page, per_page=per_page): (index, adapter)
                for index, adapter, kind in tasks
            }
            for future in as_completed(future_map):
                index, adapter = future_map[future]
                try:
                    results[index] = future.result()
                except Exception as exc:
                    task_errors[index] = SearchError(adapter.source_name, str(exc))

        for index, _adapter, _kind in tasks:
            if index in results:
                assets.extend(results[index])
            if index in task_errors:
                errors.append(task_errors[index])
        return SearchResult(assets=_dedupe_assets(assets), errors=errors)

    def _route_kinds(self, query: str, category: str) -> list[AssetKind]:
        if category == "video":
            return [AssetKind.VIDEO]
        if category == "image":
            return [AssetKind.IMAGE]
        if category == "music":
            return [AssetKind.MUSIC]
        if category == "sfx":
            return [AssetKind.SFX]
        if category == "3d":
            return [AssetKind.MODEL_3D]
        if category == "auto":
            return [_infer_kind(query)]
        return [AssetKind.VIDEO, AssetKind.IMAGE, AssetKind.MUSIC, AssetKind.SFX]


def _infer_kind(query: str) -> AssetKind:
    normalized = query.lower()
    if any(word in normalized for word in MUSIC_WORDS):
        return AssetKind.MUSIC
    if any(word in normalized for word in SFX_WORDS):
        return AssetKind.SFX
    if any(word in normalized for word in IMAGE_WORDS):
        return AssetKind.IMAGE
    if any(word in normalized for word in VISUAL_WORDS):
        return AssetKind.VIDEO
    return AssetKind.VIDEO


def _dedupe_assets(assets: list[Asset]) -> list[Asset]:
    deduped: list[Asset] = []
    seen: set[tuple[str, str]] = set()
    for asset in assets:
        key = (asset.source, asset.id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(asset)
    return deduped
