from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_NAME = "api_keys.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "cache_dir": "~/.davinci_plugins/cache",
    "license_policy": {
        "allow_non_commercial": False,
        "require_attribution_confirmation": True,
    },
    "pexels": {"api_key": ""},
    "pixabay": {"api_key": ""},
    "freesound": {
        "client_id": "",
        "client_secret_or_api_key": "",
        "oauth_access_token": "",
    },
    "mixkit": {"enabled": True},
}


@dataclass(slots=True)
class LicensePolicy:
    allow_non_commercial: bool = False
    require_attribution_confirmation: bool = True


@dataclass(slots=True)
class AppConfig:
    config_path: Path
    cache_dir: Path
    pexels_api_key: str = ""
    pixabay_api_key: str = ""
    freesound_client_id: str = ""
    freesound_api_key: str = ""
    freesound_oauth_access_token: str = ""
    mixkit_enabled: bool = True
    license_policy: LicensePolicy = field(default_factory=LicensePolicy)


def _expand_path(path: str | Path) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(str(path)))).resolve()


def candidate_config_paths(explicit_path: str | None = None) -> list[Path]:
    if explicit_path:
        return [_expand_path(explicit_path)]
    cwd_path = Path.cwd() / DEFAULT_CONFIG_NAME
    user_path = _expand_path("~/.davinci_plugins/api_keys.json")
    example_path = Path(__file__).resolve().parent.parent / "api_keys.example.json"
    return [cwd_path, user_path, example_path]


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a JSON object: {path}")
    return data


def read_config_json(explicit_path: str | None = None) -> tuple[Path, dict[str, Any]]:
    selected_path = None
    raw: dict[str, Any] = {}
    for path in candidate_config_paths(explicit_path):
        if path.exists():
            selected_path = path
            raw = _read_json(path)
            break
    if selected_path is None:
        selected_path = candidate_config_paths(explicit_path)[0]
        raw = {}
    return selected_path, _merge_config(DEFAULT_CONFIG, raw)


def update_key_config(explicit_path: str | None, updates: dict[str, Any], deletes: dict[str, bool] | None = None) -> AppConfig:
    config_path, raw = read_config_json(explicit_path)
    deletes = deletes or {}

    _ensure_section(raw, "pexels")
    _ensure_section(raw, "pixabay")
    _ensure_section(raw, "freesound")
    _ensure_section(raw, "mixkit")

    key_map = {
        "pexels_api_key": ("pexels", "api_key"),
        "pixabay_api_key": ("pixabay", "api_key"),
        "freesound_client_id": ("freesound", "client_id"),
        "freesound_api_key": ("freesound", "client_secret_or_api_key"),
        "freesound_oauth_access_token": ("freesound", "oauth_access_token"),
    }
    for name, (section, key) in key_map.items():
        if deletes.get(name):
            raw[section][key] = ""
            continue
        if name in updates:
            value = _clean_value(updates.get(name, ""))
            if value:
                raw[section][key] = value

    if "mixkit_enabled" in updates:
        raw["mixkit"]["enabled"] = bool(updates["mixkit_enabled"])

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as handle:
        json.dump(raw, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return load_config(str(config_path))


def load_config(explicit_path: str | None = None) -> AppConfig:
    selected_path, raw = read_config_json(explicit_path)

    license_raw = raw.get("license_policy", {}) if isinstance(raw.get("license_policy", {}), dict) else {}
    policy = LicensePolicy(
        allow_non_commercial=bool(license_raw.get("allow_non_commercial", False)),
        require_attribution_confirmation=bool(license_raw.get("require_attribution_confirmation", True)),
    )

    pexels = _section(raw, "pexels")
    pixabay = _section(raw, "pixabay")
    freesound = raw.get("freesound", {}) if isinstance(raw.get("freesound", {}), dict) else {}
    mixkit = raw.get("mixkit", {}) if isinstance(raw.get("mixkit", {}), dict) else {}
    freesound_api_key = _first_non_empty(
        freesound,
        "client_secret_or_api_key",
        "client_secret",
        "api_key",
        "token",
    )
    freesound_oauth_access_token = _first_non_empty(
        freesound,
        "oauth_access_token",
        "access_token",
    )

    cache_dir = _expand_path(raw.get("cache_dir", "~/.davinci_plugins/cache"))
    return AppConfig(
        config_path=selected_path,
        cache_dir=cache_dir,
        pexels_api_key=_clean_value(pexels.get("api_key", "")),
        pixabay_api_key=_clean_value(pixabay.get("api_key", "")),
        freesound_client_id=_clean_value(freesound.get("client_id", "")),
        freesound_api_key=freesound_api_key,
        freesound_oauth_access_token=freesound_oauth_access_token,
        mixkit_enabled=bool(mixkit.get("enabled", True)),
        license_policy=policy,
    )


def _first_non_empty(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = _clean_value(data.get(key, ""))
        if value:
            return value
    return ""


def _section(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key, {})
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return {"api_key": value}
    return {}


def _ensure_section(raw: dict[str, Any], key: str) -> None:
    if not isinstance(raw.get(key), dict):
        raw[key] = {}


def _clean_value(value: object) -> str:
    text = str(value).strip()
    if _is_placeholder(text):
        return ""
    return text


def _is_placeholder(value: str) -> bool:
    return value.startswith("PASTE_") or value.startswith("YOUR_")


def _merge_config(defaults: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key, value in defaults.items():
        if isinstance(value, dict):
            raw_value = raw.get(key, {})
            merged[key] = _merge_config(value, raw_value) if isinstance(raw_value, dict) else raw_value
        else:
            merged[key] = raw.get(key, value)
    for key, value in raw.items():
        if key not in merged:
            merged[key] = value
    return merged
