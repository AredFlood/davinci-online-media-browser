"""Render CapCut-style thumbnail cards for the results grid.

Each card is a fixed-size QPixmap built from a fetched thumbnail (or a typed
placeholder) with small corner badges: source platform (top-left), license
(top-right) and clip duration (bottom-right).
"""
from __future__ import annotations

from ..models import Asset, AssetKind
from .qt_compat import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPen,
    QPixmap,
    QRect,
    QSize,
    Qt,
)


_SOURCE_COLORS = {
    "pexels": "#05a081",
    "pixabay": "#2a7de1",
    "freesound": "#d9772b",
    "mixkit": "#7a3ff2",
}

_LICENSE_COLORS = {
    "NC": "#d9534f",
    "BY": "#d9a441",
    "CC0": "#3aa657",
    "©": "#6b7280",
}

_KIND_GLYPH = {
    AssetKind.VIDEO: "▶ VIDEO",
    AssetKind.IMAGE: "🖼 IMAGE",
    AssetKind.MUSIC: "♪ MUSIC",
    AssetKind.SFX: "🔊 SFX",
    AssetKind.MODEL_3D: "◆ 3D",
    AssetKind.TEMPLATE: "▤ TEMPLATE",
}


def make_card_pixmap(data: bytes, asset: Asset, size: QSize) -> QPixmap:
    """Build a card from raw thumbnail bytes; falls back to a placeholder."""
    base = QPixmap()
    if data:
        base.loadFromData(data)
    if base.isNull():
        return make_placeholder_pixmap(asset, size)

    canvas = QPixmap(size)
    canvas.fill(QColor("#101216"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    scaled = base.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = (size.width() - scaled.width()) // 2
    y = (size.height() - scaled.height()) // 2
    painter.drawPixmap(x, y, scaled)
    _draw_badges(painter, asset, size)
    painter.end()
    return canvas


def make_placeholder_pixmap(asset: Asset, size: QSize) -> QPixmap:
    """A neutral card used while a thumbnail loads or when none is available."""
    canvas = QPixmap(size)
    canvas.fill(QColor("#1c1f25"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(QPen(QColor("#6b7280")))
    font = QFont()
    font.setPointSize(11)
    font.setBold(True)
    painter.setFont(font)
    glyph = _KIND_GLYPH.get(asset.kind, asset.kind.value.upper())
    painter.drawText(canvas.rect(), Qt.AlignCenter, glyph)
    _draw_badges(painter, asset, size)
    painter.end()
    return canvas


def _draw_badges(painter: QPainter, asset: Asset, size: QSize) -> None:
    source_color = _SOURCE_COLORS.get(asset.source.lower(), "#444a57")
    _draw_badge(painter, asset.source, QColor(source_color), QColor("#ffffff"), size, corner="tl")

    badge = asset.license_badge
    if badge:
        color = QColor(_LICENSE_COLORS.get(badge, "#6b7280"))
        _draw_badge(painter, badge, color, QColor("#ffffff"), size, corner="tr")

    if asset.duration:
        _draw_badge(
            painter,
            _format_duration(asset.duration),
            QColor(0, 0, 0, 170),
            QColor("#ffffff"),
            size,
            corner="br",
        )


def _draw_badge(
    painter: QPainter,
    text: str,
    bg: QColor,
    fg: QColor,
    size: QSize,
    *,
    corner: str,
) -> None:
    if not text:
        return
    font = QFont()
    font.setPointSize(8)
    font.setBold(True)
    painter.setFont(font)
    metrics = painter.fontMetrics()
    pad_x, pad_y, margin = 6, 3, 6
    text_w = metrics.horizontalAdvance(text)
    text_h = metrics.height()
    box_w = text_w + pad_x * 2
    box_h = text_h + pad_y * 2

    if corner == "tl":
        left, top = margin, margin
    elif corner == "tr":
        left, top = size.width() - box_w - margin, margin
    elif corner == "bl":
        left, top = margin, size.height() - box_h - margin
    else:  # br
        left, top = size.width() - box_w - margin, size.height() - box_h - margin

    rect = QRect(int(left), int(top), int(box_w), int(box_h))
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(bg))
    painter.drawRoundedRect(rect, 4, 4)
    painter.setPen(QPen(fg))
    painter.drawText(rect, Qt.AlignCenter, text)


def _format_duration(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:d}:{secs:02d}"
