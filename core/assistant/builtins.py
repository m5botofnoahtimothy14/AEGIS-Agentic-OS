from __future__ import annotations

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import structlog

from .registry import tool

logger = structlog.get_logger("SATURDAY.Assistant.Builtins")


class _ToolContext:
    def __init__(self) -> None:
        self.storage_dir: Path = Path("data")
        self.agent: Any = None
        self.memory: Any = None
        self.reminders: Any = None
        self.profile: Any = None


_ctx = _ToolContext()


def configure_tool_context(
    storage_dir: Any = None,
    agent: Any = None,
    memory: Any = None,
    reminders: Any = None,
    profile: Any = None,
) -> None:
    if storage_dir is not None:
        _ctx.storage_dir = Path(storage_dir)
    if agent is not None:
        _ctx.agent = agent
    if memory is not None:
        _ctx.memory = memory
    if reminders is not None:
        _ctx.reminders = reminders
    if profile is not None:
        _ctx.profile = profile


def _notes_dir() -> Path:
    notes = _ctx.storage_dir / "notes"
    notes.mkdir(parents=True, exist_ok=True)
    return notes


@tool("get_time", "Tell the current time")
def get_time() -> str:
    return f"It's {datetime.now().strftime('%I:%M %p')}."


@tool("get_date", "Tell today's date")
def get_date() -> str:
    return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."


@tool("system_status", "Report CPU, memory and disk usage")
def system_status() -> str:
    try:
        import psutil

        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        return f"System status. CPU {cpu:.1f}%, memory {mem:.1f}%, disk {disk:.1f}%."
    except Exception as e:
        logger.warning("system_status failed", error=str(e))
        return "System status is unavailable right now."


@tool("help", "List the available SATURDAY assistant capabilities")
def assist_help() -> str:
    from .registry import all_tools

    names = ", ".join(spec.name for spec in all_tools())
    return f"I can help with: {names}."


@tool("remember", "Store a fact or preference in local memory", params={"fact": {"type": "str", "required": True, "desc": "the fact or preference to remember"}})
def remember(fact: str) -> str:
    if _ctx.agent is not None and hasattr(_ctx.agent, "_remember"):
        _ctx.agent._remember(f"remember {fact}")
        return f"I remembered that: {fact}."
    if _ctx.memory is not None and hasattr(_ctx.memory, "store_preference"):
        _ctx.memory.store_preference(fact)
        return f"I remembered that: {fact}."
    return f"I remembered that: {fact}."


@tool("show_memory", "Show what SATURDAY remembers about you")
def show_memory() -> str:
    if _ctx.agent is not None and hasattr(_ctx.agent, "_show_memory"):
        snapshot = _ctx.agent._show_memory()
        facts = snapshot.get("facts", [])
        likes = snapshot.get("preferences", {}).get("likes", [])
    elif _ctx.memory is not None and hasattr(_ctx.memory, "get_snapshot"):
        snapshot = _ctx.memory.get_snapshot()
        facts = snapshot.get("facts", [])
        likes = snapshot.get("preferences", {}).get("likes", [])
    else:
        return "No local memory stored yet."
    parts = [f"- {item}" for item in likes[:5]]
    parts += [f"- {item}" for item in facts[:5]]
    if not parts:
        return "No local memory stored yet."
    return "Things I remember:\n" + "\n".join(parts)


@tool("create_note", "Save a short note to the local notes folder", params={"title": {"type": "str", "required": True, "desc": "note contents"}})
def create_note(title: str) -> str:
    body = str(title).strip() or "Offline note created by SATURDAY."
    slug = re.sub(r"[^a-z0-9]+", "-", body.lower()).strip("-") or "note"
    path = _notes_dir() / f"{slug}.md"
    path.write_text(body + "\n", encoding="utf-8")
    return f"I saved a note at {path.name}."


@tool("list_notes", "List saved local notes")
def list_notes() -> str:
    notes = sorted(path.name for path in _notes_dir().glob("*.md"))
    if not notes:
        return "You don't have any saved notes yet."
    listing = "\n".join(f"- {note}" for note in notes)
    return f"Saved notes:\n{listing}"


@tool("set_reminder", "Set a timed reminder", params={"minutes": {"type": "int", "required": True, "desc": "minutes from now"}, "message": {"type": "str", "required": True, "desc": "reminder text"}})
def set_reminder(minutes: int, message: str) -> str:
    if _ctx.reminders is None:
        return "Reminders are not enabled right now."
    _ctx.reminders.add_reminder_in_minutes(int(minutes), str(message))
    return f"Reminder set for {int(minutes)} minutes from now: {message}."


@tool("list_tasks", "List active reminders and tasks")
def list_tasks() -> str:
    if _ctx.reminders is None:
        return "No scheduled tasks right now."
    return _ctx.reminders.list_active_text()


@tool("set_profile", "Learn a piece of information about the user", params={"key": {"type": "str", "required": True, "desc": "profile key, e.g. name"}, "value": {"type": "str", "required": True, "desc": "profile value"}})
def set_profile(key: str, value: str) -> str:
    if _ctx.profile is not None:
        _ctx.profile.update(key.strip().lower(), value.strip())
    return f"Noted: your {key.strip().lower()} is {value.strip()}."