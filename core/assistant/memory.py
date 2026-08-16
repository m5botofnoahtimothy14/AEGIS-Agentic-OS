from __future__ import annotations

import json
import math
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import structlog

logger = structlog.get_logger("SATURDAY.Assistant.Memory")

_THRESHOLD = 0.45
_MODEL = None
_MODEL_LOCK = threading.Lock()


def _get_model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        with _MODEL_LOCK:
            if _MODEL is None:
                _MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _MODEL


def _encode(texts: List[str]) -> Optional[np.ndarray]:
    try:
        model = _get_model()
        return np.asarray(model.encode(list(texts), normalize_embeddings=True), dtype=np.float32)
    except Exception as e:
        logger.debug("Embedder unavailable; using keyword recall", error=str(e))
        return None


class SemanticMemory:
    def __init__(self, storage_dir: Any = "data", threshold: float = _THRESHOLD) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.storage_dir / "semantic_memory.json"
        self.threshold = threshold
        self.exchanges: List[Dict[str, Any]] = []
        self.facts: List[str] = []
        self.preferences: Dict[str, List[str]] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            self.exchanges = data.get("exchanges", [])
            self.facts = data.get("facts", [])
            self.preferences = data.get("preferences", {})
        except (json.JSONDecodeError, OSError):
            logger.warning("Failed to load semantic memory; starting fresh")

    def _persist(self) -> None:
        payload = {
            "exchanges": self.exchanges[-500:],
            "facts": self.facts,
            "preferences": self.preferences,
            "saved_at": datetime.now().isoformat(),
        }
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def store(self, user: str, assistant: str) -> None:
        with self._lock:
            self.exchanges.append(
                {"user": user, "assistant": assistant, "timestamp": time.time()}
            )
            self._persist()

    def store_preference(self, fact: str) -> None:
        with self._lock:
            phrase = str(fact).strip()
            if "like" in phrase.lower() or "prefer" in phrase.lower() or "love" in phrase.lower():
                bucket = self.preferences.setdefault("likes", [])
                if phrase not in bucket:
                    bucket.append(phrase)
            elif phrase and phrase not in self.facts:
                self.facts.append(phrase)
            self._persist()

    def get_snapshot(self) -> Dict[str, Any]:
        return {
            "facts": list(self.facts),
            "preferences": {k: list(v) for k, v in self.preferences.items()},
        }

    def recall(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        with self._lock:
            entries = list(self.exchanges)
        if not entries:
            return []
        texts = [f"{e.get('user', '')} {e.get('assistant', '')}" for e in entries]
        vectors = _encode(texts)
        if vectors is None:
            return self._keyword_recall(query, entries, top_k)
        qvec = _encode([query])[0]
        scores = vectors @ qvec
        order = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in order:
            score = float(scores[idx])
            if score < self.threshold:
                continue
            results.append({"user": entries[idx].get("user", ""), "assistant": entries[idx].get("assistant", ""), "score": round(score, 3)})
        return results

    def _keyword_recall(self, query: str, entries: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        if not tokens:
            return []
        scored = []
        for entry in entries[-200:]:
            text = f"{entry.get('user', '')} {entry.get('assistant', '')}".lower()
            overlap = len(tokens & set(re.findall(r"[a-z0-9]+", text)))
            if overlap > 0:
                scored.append((overlap, entry))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {"user": entry.get("user", ""), "assistant": entry.get("assistant", ""), "score": round(score / max(1, len(tokens)), 3)}
            for score, entry in scored[:top_k]
        ]

    def context_block(self, query: str, top_k: int = 2) -> str:
        recall = self.recall(query, top_k=top_k)
        if not recall:
            return ""
        lines = []
        for item in recall:
            lines.append(f"Memory: User said '{item['user']}', I replied '{item['assistant']}'.")
        return "\n".join(lines)