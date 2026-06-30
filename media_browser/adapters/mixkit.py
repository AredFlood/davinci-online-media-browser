from __future__ import annotations

from html import unescape
import re
from urllib.parse import quote_plus

from ..models import Asset, AssetKind
from ..utils.http import request_bytes
from .base import MediaAdapter


class MixkitAdapter(MediaAdapter):
    source_name = "Mixkit"
    supported_kinds = {AssetKind.MUSIC, AssetKind.SFX}

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def is_available(self) -> bool:
        return self.enabled

    def search(self, query: str, kind: AssetKind, *, page: int = 1, per_page: int = 20) -> list[Asset]:
        if not self.enabled or kind not in self.supported_kinds:
            return []
        if kind == AssetKind.MUSIC:
            url = "https://mixkit.co/free-stock-music/"
        else:
            url = "https://mixkit.co/free-sound-effects/"
        return _scrape_mixkit_listing(self.source_name, kind, url, query=query, page=page, per_page=per_page)


def _scrape_mixkit_listing(source_name: str, kind: AssetKind, url: str, *, query: str, page: int, per_page: int) -> list[Asset]:
    listing_url = f"{url}?page={page}&q={_query(query)}"
    html = request_bytes(listing_url).text
    blocks = re.findall(
        r'<div class="item-grid__item">(.*?)(?=<div class="item-grid__item">|</main>)',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assets: list[Asset] = []
    for block in blocks:
        if len(assets) >= per_page:
            break
        preview_url = _extract_attr(block, "data-audio-player-preview-url-value")
        item_id = _extract_attr(block, "data-audio-player-item-id-value")
        item_type = _extract_attr(block, "data-audio-player-item-type-value")
        if not preview_url or not item_id:
            continue
        if kind == AssetKind.MUSIC and item_type != "music":
            continue
        if kind == AssetKind.SFX and item_type != "sfx":
            continue
        title = _extract_tag_text(block, "h2", "item-grid-card__title")
        if not title:
            title = f"Mixkit {kind.value} {item_id}"
        author = _extract_author(block)
        duration = _duration_to_seconds(_extract_duration(block))
        tags = _extract_meta_links(block)
        download_path = (
            f"/free-stock-music/download/{item_id}/?context=item+grid"
            if kind == AssetKind.MUSIC
            else f"/free-sound-effects/download/{item_id}/?context=item+grid"
        )
        assets.append(
            Asset(
                id=item_id,
                source=source_name,
                kind=kind,
                title=title,
                author=author,
                license_name="Mixkit Free License",
                license_url="https://mixkit.co/license/",
                source_url=f"https://mixkit.co{download_path}",
                preview_url=preview_url,
                download_url=preview_url,
                duration=duration,
                tags=tags,
                metadata={
                    "scraped": True,
                    "listing_url": listing_url,
                    "download_modal": download_path,
                    "download_note": "Mixkit has no public API; this uses the public MP3 preview URL found on the listing page.",
                },
            )
        )
    return assets


def _extract_attr(block: str, attr_name: str) -> str:
    match = re.search(rf'{re.escape(attr_name)}="([^"]*)"', block, flags=re.IGNORECASE)
    return unescape(match.group(1)).strip() if match else ""


def _extract_tag_text(block: str, tag: str, class_name: str) -> str:
    match = re.search(
        rf'<{tag}[^>]*class="{re.escape(class_name)}"[^>]*>(.*?)</{tag}>',
        block,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return _strip_html(match.group(1)).strip() if match else ""


def _extract_author(block: str) -> str:
    match = re.search(
        r'<p[^>]*class="item-grid-music-preview__author"[^>]*>(.*?)</p>',
        block,
        flags=re.IGNORECASE | re.DOTALL,
    )
    author = _strip_html(match.group(1)).strip() if match else ""
    return re.sub(r"^by\s+", "", author, flags=re.IGNORECASE).strip()


def _extract_duration(block: str) -> str:
    match = re.search(
        r'<div[^>]*data-test-id="duration"[^>]*>(.*?)</div>',
        block,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return _strip_html(match.group(1)).strip() if match else ""


def _extract_meta_links(block: str) -> list[str]:
    labels = re.findall(
        r'<a[^>]*class="meta-links__link"[^>]*>(.*?)</a>',
        block,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return [_strip_html(label).strip() for label in labels if _strip_html(label).strip()]


def _duration_to_seconds(value: str) -> float | None:
    if not value:
        return None
    parts = value.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        return None
    return None


def _query(value: str) -> str:
    return quote_plus(value.strip())


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = re.sub(r"\s+", " ", text)
    return unescape(text)
