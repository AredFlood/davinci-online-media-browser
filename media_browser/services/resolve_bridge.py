from __future__ import annotations

import importlib
import sys
from pathlib import Path

from ..models import Asset
from .metadata import build_resolve_metadata


class ResolveUnavailable(RuntimeError):
    pass


class ResolveBridge:
    def __init__(self, resolve: object | None = None):
        self.resolve = resolve or get_resolve()

    def import_media(self, media_paths: list[Path], assets: list[Asset]) -> list[object]:
        if not media_paths:
            return []
        project = self.resolve.GetProjectManager().GetCurrentProject()
        if not project:
            raise ResolveUnavailable("No current DaVinci Resolve project is open.")
        media_pool = project.GetMediaPool()
        if not media_pool:
            raise ResolveUnavailable("Current project has no media pool.")

        imported = media_pool.ImportMedia([str(path) for path in media_paths])
        if not imported:
            raise ResolveUnavailable("Resolve did not import any media. Check file codec/path support.")
        for item, asset in zip(imported, assets, strict=False):
            self._set_metadata(item, asset)
        return imported

    def _set_metadata(self, media_pool_item: object, asset: Asset) -> None:
        metadata = build_resolve_metadata(asset)
        try:
            media_pool_item.SetMetadata(metadata)
            return
        except Exception:
            pass
        for key, value in metadata.items():
            try:
                media_pool_item.SetMetadata(key, value)
            except Exception:
                continue


def get_resolve() -> object:
    module = _import_resolve_module()
    resolve = module.scriptapp("Resolve")
    if not resolve:
        raise ResolveUnavailable("DaVinci Resolve scripting app is not available.")
    return resolve


def _import_resolve_module() -> object:
    module_names = ("DaVinciResolveScript", "bmd")
    for module_name in module_names:
        try:
            return importlib.import_module(module_name)
        except ImportError:
            continue
    for path in _resolve_module_paths():
        if path.exists() and str(path) not in sys.path:
            sys.path.append(str(path))
    for module_name in module_names:
        try:
            return importlib.import_module(module_name)
        except ImportError:
            continue
    raise ResolveUnavailable(
        "Could not import DaVinciResolveScript. Run inside Resolve or install the Resolve scripting modules."
    )


def _resolve_module_paths() -> list[Path]:
    return [
        Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"),
        Path.home() / "Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules",
        Path("C:/ProgramData/Blackmagic Design/DaVinci Resolve/Support/Developer/Scripting/Modules"),
        Path("/opt/resolve/Developer/Scripting/Modules"),
    ]
