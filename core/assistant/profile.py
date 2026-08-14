from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger("SATURDAY.Assistant.Profile")


class UserProfile:
    def __init__(self, storage_dir: Any = "data") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.storage_dir / "profile.json"
        self.profile: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            self.profile = data.get("profile", {})
        except (json.JSONDecodeError, OSError):
            logger.warning("Failed to load user profile; starting fresh")

    def _persist(self) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump({"profile": self.profile}, handle, indent=2)

    def update(self, key: str, value: str) -> None:
        if not key or not value:
            return
        self.profile[key.strip().lower()] = str(value).strip()
        self._persist()

    def get(self, key: str, default: Any = None) -> Any:
        return self.profile.get(key, default)

    def get_context(self) -> str:
        if not self.profile:
            return ""
        return "\n".join(f"{key}: {value}" for key, value in self.profile.items())

    def capture(self, text: str) -> bool:
        """Greedily learn 'my name is X' / 'i like Y' style details. Returns True
        if anything was captured."""
        low = text.lower()
        changed = False
        name_match = re.search(r"(?:my name is|call me|you can call me|my name's)\s+([a-zA-Z]+)", low)
        if name_match:
            full = re.search(r"(?:my name is|call me|you can call me|my name's)\s+(.+)", text)
            value = (full.group(1).strip() if full else name_match.group(1)).rstrip(".!")
            self.update("name", value)
            changed = True
        likes = re.search(r"i (?:really )?(?:like|love|prefer)\s+(.+)", low)
        if likes:
            value = text[likes.start():].split(",")[0].lstrip(" ").rstrip(".!")
            self.update("interests", value)
            changed = True
        return changed