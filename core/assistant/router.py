from __future__ import annotations

import re
from typing import Optional

from .registry import ToolCall
from .reminders import parse_reminder


_TIME = ("what time", "what's the time", "current time", "tell me the time", "what is the time")
_DATE = ("what date", "what's the date", "today's date", "tell me the date", "what day is it", "what day is today")
_STATUS = (
    "system status",
    "system condition",
    "system info",
    "system information",
    "cpu usage",
    "memory usage",
    "how are you",
    "how's the system",
    "are you running",
    "system health",
)
_HELP = ("what can you do", "capabilities", "help", "who are you", "what are you", "features")
_REMEMBER = ("remember that", "remember ", "note that", "store that", "learn that")
_SHOW_MEMORY = ("what do you remember", "show memory", "show memories", "what do you know about me", "memory")
_NOTE = (
    "write note",
    "write a note",
    "make a note",
    "create a note",
    "create note",
    "save a note",
    "save note",
    "take a note",
    "take note",
    "add a note",
)
_LIST_NOTES = ("list notes", "show notes", "show my notes", "my notes", "list my notes")
_LIST_TASKS = (
    "list tasks",
    "show tasks",
    "list reminders",
    "show reminders",
    "active reminders",
    "list my tasks",
)
_NAME = ("my name is ", "call me ", "you can call me ", "my name's ")
_NAME_KEY = re.compile(r"(?:my name is|call me|you can call me|my name's)\s+(.+)", re.IGNORECASE)


def resolve_keyword_tool(query: str, raw_query: Optional[str] = None) -> Optional[ToolCall]:
    """Deterministic, LLM-free fast path.

    Maps a known spoken/typed command phrase to a registered ToolCall, or None.
    A miss returns None and the caller falls back to the LLM tool agent / chat.
    First match wins; the reminder parser runs before generic helpers since it
    needs the exact trigger + time amount.
    """
    text = (query or "").strip()
    raw = raw_query if raw_query is not None else text
    low = text.lower()

    reminder = parse_reminder(low)
    if reminder is not None:
        return ToolCall("set_reminder", reminder)

    if any(phrase in low for phrase in _REMEMBER):
        body = re.sub(r"^(remember that|remember|note that|store that|learn that)\s+", "", low, flags=re.IGNORECASE).strip()
        if body:
            return ToolCall("remember", {"fact": body})

    if any(phrase in low for phrase in _SHOW_MEMORY):
        return ToolCall("show_memory", {})

    if any(phrase in low for phrase in _TIME):
        return ToolCall("get_time", {})

    if any(phrase in low for phrase in _DATE):
        return ToolCall("get_date", {})

    if any(phrase in low for phrase in _STATUS):
        return ToolCall("system_status", {})

    if any(phrase in low for phrase in _HELP):
        return ToolCall("help", {})

    if any(phrase in low for phrase in _NOTE):
        body = re.sub(r"^(write|make|create|save|take|add)(\s+a|\s+an)?\s+note\s*", "", low, flags=re.IGNORECASE).strip()
        return ToolCall("create_note", {"title": body or "note"})

    if any(phrase in low for phrase in _LIST_NOTES):
        return ToolCall("list_notes", {})

    if any(phrase in low for phrase in _LIST_TASKS):
        return ToolCall("list_tasks", {})

    match = _NAME_KEY.search(raw)
    if match:
        value = match.group(1).strip()
        if value:
            return ToolCall("set_profile", {"key": "name", "value": value})

    return None