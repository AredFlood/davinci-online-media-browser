from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class SettingsStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def default(cls) -> "SettingsStore":
        return cls(Path.home() / ".davinci_plugins" / "settings.json")

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def write(self, data: dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)

    def should_show_license_notice(self) -> bool:
        value = str(self.read().get("license_notice_suppressed_until", "")).strip()
        if not value:
            return True
        try:
            until = datetime.fromisoformat(value)
        except ValueError:
            return True
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= until

    def suppress_license_notice_for_days(self, days: int = 30) -> None:
        data = self.read()
        until = datetime.now(timezone.utc) + timedelta(days=days)
        data["license_notice_suppressed_until"] = until.isoformat()
        self.write(data)
