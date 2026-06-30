from __future__ import annotations

from ..models import Asset


def build_resolve_metadata(asset: Asset) -> dict[str, str]:
    attribution = build_attribution(asset)
    comments = [
        f"Source: {asset.source}",
        f"Original URL: {asset.source_url}",
        f"License: {asset.license_name} {asset.license_url}".strip(),
    ]
    if attribution:
        comments.append(f"Attribution: {attribution}")
    if asset.tags:
        comments.append(f"Keywords: {', '.join(asset.tags)}")
    if asset.metadata.get("download_note"):
        comments.append(str(asset.metadata["download_note"]))
    return {
        "Comments": "\n".join(part for part in comments if part and not part.endswith(": ")),
        "Keywords": ", ".join(asset.tags + [asset.source, asset.kind.value]),
    }


def build_attribution(asset: Asset) -> str:
    if not asset.author:
        return ""
    if asset.author_url:
        return f"{asset.author} ({asset.author_url})"
    return asset.author
