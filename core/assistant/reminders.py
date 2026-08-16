from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import structlog

logger = structlog.get_logger("SATURDAY.Assistant.Reminders")


_UNIT_MINUTES = {
    "second": 1 / 60,
    "seconds": 1 / 60,
    "sec": 1 / 60,
    "secs": 1 / 60,
    "minute": 1,
    "minutes": 1,
    "min": 1,
    "mins": 1,
    "hour": 60,
    "hours": 60,
    "hr": 60,
    "hrs": 60,
}

_UNIT_GROUP = "|".join(_UNIT_MINUTES)
_AMOUNT_GROUP = r"\d+|a|an|half an?"
_FORWARD = re.compile(rf"remind me in ({_AMOUNT_GROUP}) ({_UNIT_GROUP}) to (.+)")
_REVERSED = re.compile(rf"remind me to (.+?) in ({_AMOUNT_GROUP}) ({_UNIT_GROUP})\b")


def _amount_to_number(raw: str) -> float:
    if raw in ("a", "an"):
        return 1
    if raw.startswith("half"):
        return 0.5
    return float(raw)


def _minutes(amount_raw: str, unit: str):
    value = _amount_to_number(amount_raw) * _UNIT_MINUTES[unit]
    if float(value).is_integer():
        return int(value)
    return round(value, 2)


def parse_reminder(query: str) -> Optional[Dict[str, Any]]:
    """Parse 'remind me in 5 minutes to X' / 'remind me to X in 10 seconds'.

    Returns {'minutes', 'message'} or None.
    """
    query = str(query).lower()
    match = _FORWARD.search(query)
    if match:
        return {"minutes": _minutes(match.group(1), match.group(2)), "message": match.group(3).strip()}
    match = _REVERSED.search(query)
    if match:
        return {"minutes": _minutes(match.group(2), match.group(3)), "message": match.group(1).strip()}
    return None


class ReminderManager:
    def __init__(self, storage_dir: Any = "data", on_fire: Optional[Callable[[Dict[str, Any]], Any]] = None) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.storage_dir / "reminders.json"
        self.on_fire = on_fire or self._default_announce
        self.tasks: List[Dict[str, Any]] = []
        self._timers: Dict[str, threading.Timer] = {}
        self._lock = threading.Lock()
        self.running = False
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            self.tasks = data.get("tasks", []) if isinstance(data, dict) else []
        except (json.JSONDecodeError, OSError):
            self.tasks = []

    def _persist(self) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump({"tasks": self.tasks}, handle, indent=2)

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        now = datetime.now()
        survivors: List[Dict[str, Any]] = []
        for task in self.tasks:
            if "id" not in task:
                task["id"] = uuid.uuid4().hex
            try:
                task_time = datetime.fromisoformat(task["time"])
            except ValueError:
                continue
            remaining = (task_time - now).total_seconds()
            if remaining <= 0:
                logger.info("Skipping expired reminder", message=task.get("message"))
                continue
            survivors.append(task)
            self._schedule(task, remaining)
        if len(survivors) != len(self.tasks):
            self.tasks = survivors
            self._persist()

    def _default_announce(self, task: Dict[str, Any]) -> None:
        logger.info("Reminder fired", message=task.get("message"))

    def add_reminder_in_minutes(self, minutes: float, message: str) -> Dict[str, Any]:
        trigger_time = datetime.now() + timedelta(minutes=max(0.0, float(minutes)))
        task = {"id": uuid.uuid4().hex, "time": trigger_time.isoformat(), "message": str(message)}
        with self._lock:
            self.tasks.append(task)
            self._persist()
        self._schedule(task, max(0.0, float(minutes)) * 60)
        return task

    def _schedule(self, task: Dict[str, Any], delay_seconds: float) -> None:
        timer = threading.Timer(max(0.0, delay_seconds), self._fire, args=(task,))
        timer.daemon = True
        timer.start()
        self._timers[task["id"]] = timer

    def _fire(self, task: Dict[str, Any]) -> None:
        try:
            self.on_fire(task)
        finally:
            with self._lock:
                self.tasks = [t for t in self.tasks if t.get("id") != task.get("id")]
                self._persist()
            self._timers.pop(task.get("id"), None)

    def list_active(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {"id": t.get("id"), "time": t.get("time"), "message": t.get("message")}
                for t in self.tasks
            ]

    def list_active_text(self) -> str:
        active = self.list_active()
        if not active:
            return "You don't have any scheduled reminders right now."
        lines = []
        for task in active:
            try:
                when = datetime.fromisoformat(task["time"]).strftime("%A at %I:%M %p")
            except ValueError:
                when = task.get("time")
            lines.append(f"- {task.get('message')} ({when})")
        return "Scheduled reminders:\n" + "\n".join(lines)

    def shutdown(self) -> None:
        self.running = False
        for timer in list(self._timers.values()):
            timer.cancel()
        self._timers.clear()