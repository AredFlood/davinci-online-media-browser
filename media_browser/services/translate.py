"""Best-effort Chinese -> English query translation.

Stock media APIs (Pexels/Pixabay/Freesound/Mixkit) index mostly English tags, so
a Chinese query is translated before searching. Uses the keyless MyMemory public
endpoint and silently falls back to the original text on any failure.
"""
from __future__ import annotations

import re

from ..utils.http import build_url, request_json

_CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
_LOCAL_TRANSLATIONS = {
    "走路": "walking",
    "行走": "walking",
    "跑步": "running",
    "脚步": "footsteps",
    "脚步声": "footsteps",
    "海洋": "ocean",
    "海浪": "ocean wave",
    "风": "wind",
    "风声": "wind",
    "雨": "rain",
    "雨声": "rain",
    "水": "water",
    "火": "fire",
    "烟雾": "smoke",
    "爆炸": "explosion",
    "城市": "city",
    "森林": "forest",
    "汽车": "car",
    "人群": "crowd",
    "天空": "sky",
}


def has_cjk(text: str) -> bool:
    return bool(_CJK.search(text))


def translate_query_to_english(text: str) -> str:
    """Return an English query for a Chinese ``text``; pass other text through."""
    text = text.strip()
    if not text or not has_cjk(text):
        return text
    if text in _LOCAL_TRANSLATIONS:
        return _LOCAL_TRANSLATIONS[text]
    translated = _mymemory_translate(text)
    return translated or text


def _mymemory_translate(text: str) -> str:
    try:
        url = build_url(
            "https://api.mymemory.translated.net/get",
            {"q": text, "langpair": "zh-CN|en"},
        )
        payload = request_json(url, timeout=8.0)
    except Exception:
        return ""
    if not isinstance(payload, dict):
        return ""
    data = payload.get("responseData")
    if isinstance(data, dict):
        translated = str(data.get("translatedText", "")).strip()
        # Guard against MyMemory echoing the input or an error sentence back.
        if translated and not has_cjk(translated) and not translated.upper().startswith("INVALID"):
            return translated
    return ""
