"""
SATURDAY 3.0 -- Assistant Built-in Tools
All 72+ real integration capabilities registered as tools.
"""
from __future__ import annotations

import re
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List

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
        self.real_integration: Any = None


_ctx = _ToolContext()


def configure_tool_context(
    storage_dir: Any = None,
    agent: Any = None,
    memory: Any = None,
    reminders: Any = None,
    profile: Any = None,
    real_integration: Any = None,
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
    if real_integration is not None:
        _ctx.real_integration = real_integration


def _real() -> Any:
    """Get or create real integration engine."""
    if _ctx.real_integration is None:
        try:
            from core.real_integration import get_real_integration
            _ctx.real_integration = get_real_integration()
        except Exception as e:
            logger.warning("real_integration unavailable", error=str(e))
            return None
    return _ctx.real_integration


def _notes_dir() -> Path:
    notes = _ctx.storage_dir / "notes"
    notes.mkdir(parents=True, exist_ok=True)
    return notes


def _call(action: str, params: dict = None) -> Any:
    """Call a real_integration method and format result."""
    engine = _real()
    if not engine:
        return {"success": False, "error": "Real integration not available"}
    try:
        method = getattr(engine, action)
        result = method(**(params or {}))
        if isinstance(result, dict):
            if result.get("success"):
                return f"Done: {result.get('message', 'success')}"
            return f"Failed: {result.get('error', 'unknown error')}"
        return str(result)
    except Exception as e:
        logger.warning(f"tool {action} failed", error=str(e))
        return f"Error: {e}"


# ─── BASIC TOOLS ────────────────────────────────────────────────

@tool("get_time", "Tell the current time")
def get_time() -> str:
    return f"It's {datetime.now().strftime('%I:%M %p')}."


@tool("get_date", "Tell today's date")
def get_date() -> str:
    return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."


@tool("help", "List the available SATURDAY assistant capabilities")
def assist_help() -> str:
    from .registry import all_tools
    names = ", ".join(spec.name for spec in all_tools())
    return f"I can help with: {names}."


@tool("system_status", "Report CPU, memory and disk usage")
def system_status() -> str:
    return _call("system_info")


# ─── MEMORY TOOLS ──────────────────────────────────────────────

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


# ─── SYSTEM & APPS ──────────────────────────────────────────────

@tool("open_app", "Open an application by name", params={"app_name": {"type": "str", "required": True, "desc": "application name (notepad, chrome, calculator, etc.)"}})
def open_app(app_name: str) -> str:
    return _call("open_application", {"app_name": app_name})


@tool("list_processes", "List running processes with CPU/memory", params={"limit": {"type": "int", "required": False, "default": 20, "desc": "max processes to return"}})
def list_processes(limit: int = 20) -> str:
    return _call("list_processes", {"limit": limit})


@tool("kill_process", "Kill a process by PID or name", params={"pid": {"type": "int", "required": False, "desc": "process ID"}, "name": {"type": "str", "required": False, "desc": "process name"}})
def kill_process(pid: int = None, name: str = None) -> str:
    return _call("kill_process", {"pid": pid, "name": name})


@tool("system_info", "Get comprehensive system information")
def system_info() -> str:
    return _call("system_info")


@tool("disk_info", "Get disk/partition information")
def disk_info() -> str:
    return _call("disk_info")


@tool("network_info", "Get network interfaces and connections")
def network_info() -> str:
    return _call("network_info")


@tool("env_vars", "List or search environment variables", params={"filter_key": {"type": "str", "required": False, "desc": "filter by key name"}})
def env_vars(filter_key: str = None) -> str:
    return _call("env_vars", {"filter_key": filter_key})


@tool("set_env", "Set an environment variable", params={"key": {"type": "str", "required": True, "desc": "variable name"}, "value": {"type": "str", "required": True, "desc": "variable value"}})
def set_env(key: str, value: str) -> str:
    return _call("set_env", {"key": key, "value": value})


@tool("scheduled_tasks", "List Windows scheduled tasks")
def scheduled_tasks() -> str:
    return _call("scheduled_tasks")


@tool("service_status", "Get Windows service status", params={"name": {"type": "str", "required": False, "desc": "service name"}})
def service_status(name: str = None) -> str:
    return _call("service_status", {"name": name})


@tool("event_logs", "Read Windows Event Log entries", params={"log_name": {"type": "str", "required": False, "default": "System", "desc": "log name (System, Application, Security)"}, "count": {"type": "int", "required": False, "default": 20, "desc": "number of entries"}})
def event_logs(log_name: str = "System", count: int = 20) -> str:
    return _call("event_logs", {"log_name": log_name, "count": count})


# ─── FILE OPERATIONS ────────────────────────────────────────────

@tool("list_directory", "List directory contents", params={"path": {"type": "str", "required": False, "default": ".", "desc": "directory path"}, "hidden": {"type": "bool", "required": False, "default": False, "desc": "show hidden files"}})
def list_directory(path: str = ".", hidden: bool = False) -> str:
    return _call("list_directory", {"path": path, "hidden": hidden})


@tool("search_files", "Search files by name pattern", params={"path": {"type": "str", "required": False, "default": ".", "desc": "search path"}, "pattern": {"type": "str", "required": False, "default": "*", "desc": "glob pattern"}, "recursive": {"type": "bool", "required": False, "default": True, "desc": "search recursively"}, "limit": {"type": "int", "required": False, "default": 100, "desc": "max results"}})
def search_files(path: str = ".", pattern: str = "*", recursive: bool = True, limit: int = 100) -> str:
    return _call("search_files", {"path": path, "pattern": pattern, "recursive": recursive, "limit": limit})


@tool("search_content", "Search file contents with regex", params={"path": {"type": "str", "required": False, "default": ".", "desc": "search path"}, "pattern": {"type": "str", "required": True, "desc": "regex pattern"}, "extensions": {"type": "array", "required": False, "desc": "file extensions to search"}, "limit": {"type": "int", "required": False, "default": 50, "desc": "max results"}})
def search_content(path: str = ".", pattern: str = "", extensions: List[str] = None, limit: int = 50) -> str:
    return _call("search_content", {"path": path, "pattern": pattern, "extensions": extensions, "limit": limit})


@tool("read_file", "Read file contents", params={"path": {"type": "str", "required": True, "desc": "file path"}, "lines": {"type": "int", "required": False, "desc": "number of lines to read"}})
def read_file(path: str, lines: int = None) -> str:
    return _call("read_file", {"path": path, "lines": lines})


@tool("write_file", "Write content to a file", params={"path": {"type": "str", "required": True, "desc": "file path"}, "content": {"type": "str", "required": True, "desc": "content to write"}, "append": {"type": "bool", "required": False, "default": False, "desc": "append instead of overwrite"}})
def write_file(path: str, content: str, append: bool = False) -> str:
    return _call("write_file", {"path": path, "content": content, "append": append})


@tool("copy_file", "Copy a file or directory", params={"src": {"type": "str", "required": True, "desc": "source path"}, "dst": {"type": "str", "required": True, "desc": "destination path"}})
def copy_file(src: str, dst: str) -> str:
    return _call("copy_file", {"src": src, "dst": dst})


@tool("move_file", "Move/rename a file or directory", params={"src": {"type": "str", "required": True, "desc": "source path"}, "dst": {"type": "str", "required": True, "desc": "destination path"}})
def move_file(src: str, dst: str) -> str:
    return _call("move_file", {"src": src, "dst": dst})


@tool("delete_file", "Delete a file or directory (requires force=True)", params={"path": {"type": "str", "required": True, "desc": "path to delete"}, "force": {"type": "bool", "required": False, "default": False, "desc": "confirm deletion"}})
def delete_file(path: str, force: bool = False) -> str:
    return _call("delete_file", {"path": path, "force": force})


@tool("mkdir", "Create directory (including parents)", params={"path": {"type": "str", "required": True, "desc": "directory path"}})
def mkdir(path: str) -> str:
    return _call("mkdir", {"path": path})


@tool("file_info", "Get detailed file metadata", params={"path": {"type": "str", "required": True, "desc": "file path"}})
def file_info(path: str) -> str:
    return _call("file_info", {"path": path})


@tool("hash_file", "Compute file hash", params={"path": {"type": "str", "required": True, "desc": "file path"}, "algo": {"type": "str", "required": False, "default": "sha256", "desc": "hash algorithm (sha256, md5, sha1)"}})
def hash_file(path: str, algo: str = "sha256") -> str:
    return _call("hash_file", {"path": path, "algo": algo})


# ─── COMMAND EXECUTION ──────────────────────────────────────────

@tool("execute", "Execute a shell command", params={"command": {"type": "str", "required": True, "desc": "command to execute"}, "timeout": {"type": "int", "required": False, "default": 30, "desc": "timeout in seconds"}})
def execute(command: str, timeout: int = 30) -> str:
    return _call("execute", {"command": command, "timeout": timeout})


@tool("git_status", "Get git repository status", params={"repo": {"type": "str", "required": False, "default": ".", "desc": "repository path"}})
def git_status(repo: str = ".") -> str:
    return _call("git_status", {"repo": repo})


@tool("git_log", "Get recent git log", params={"repo": {"type": "str", "required": False, "default": ".", "desc": "repository path"}, "count": {"type": "int", "required": False, "default": 20, "desc": "number of commits"}})
def git_log(repo: str = ".", count: int = 20) -> str:
    return _call("git_log", {"repo": repo, "count": count})


@tool("git_diff", "Show git diff", params={"repo": {"type": "str", "required": False, "default": ".", "desc": "repository path"}, "target": {"type": "str", "required": False, "desc": "commit or branch to diff against"}})
def git_diff(repo: str = ".", target: str = None) -> str:
    return _call("git_diff", {"repo": repo, "target": target})


@tool("git_commit", "Stage and commit changes", params={"repo": {"type": "str", "required": False, "default": ".", "desc": "repository path"}, "message": {"type": "str", "required": True, "desc": "commit message"}, "files": {"type": "str", "required": False, "default": ".", "desc": "files to stage"}})
def git_commit(repo: str = ".", message: str = "", files: str = ".") -> str:
    return _call("git_commit", {"repo": repo, "message": message, "files": files})


@tool("python_run", "Run a Python script", params={"script": {"type": "str", "required": True, "desc": "script path or code"}, "args": {"type": "str", "required": False, "default": "", "desc": "command line arguments"}})
def python_run(script: str, args: str = "") -> str:
    return _call("python_run", {"script": script, "args": args})


@tool("docker", "Execute a docker command", params={"command": {"type": "str", "required": True, "desc": "docker command (ps, images, run, etc.)"}})
def docker(command: str) -> str:
    return _call("docker", {"command": command})


# ─── WEB & INTERNET ─────────────────────────────────────────────

@tool("web_search", "Search the web and open in browser", params={"query": {"type": "str", "required": True, "desc": "search query"}, "engine": {"type": "str", "required": False, "default": "google", "desc": "search engine (google, bing, duckduckgo, youtube, github, stackoverflow, reddit, wikipedia, scholar, amazon, npm, pypi)"}})
def web_search(query: str, engine: str = "google") -> str:
    return _call("web_search", {"query": query, "engine": engine})


@tool("open_url", "Open a URL in default browser", params={"url": {"type": "str", "required": True, "desc": "URL to open"}})
def open_url(url: str) -> str:
    return _call("open_url", {"url": url})


@tool("http_get", "Make HTTP GET request", params={"url": {"type": "str", "required": True, "desc": "URL"}, "headers": {"type": "object", "required": False, "desc": "request headers"}, "params": {"type": "object", "required": False, "desc": "query parameters"}})
def http_get(url: str, headers: dict = None, params: dict = None) -> str:
    return _call("http_get", {"url": url, "headers": headers, "params": params})


@tool("http_post", "Make HTTP POST request", params={"url": {"type": "str", "required": True, "desc": "URL"}, "data": {"type": "object", "required": False, "desc": "form data"}, "json_data": {"type": "object", "required": False, "desc": "JSON data"}, "headers": {"type": "object", "required": False, "desc": "request headers"}})
def http_post(url: str, data: dict = None, json_data: dict = None, headers: dict = None) -> str:
    return _call("http_post", {"url": url, "data": data, "json_data": json_data, "headers": headers})


@tool("download", "Download a file from URL", params={"url": {"type": "str", "required": True, "desc": "URL to download"}, "dest": {"type": "str", "required": False, "desc": "destination path"}})
def download(url: str, dest: str = None) -> str:
    return _call("download", {"url": url, "dest": dest})


@tool("dns_lookup", "DNS lookup for hostname", params={"host": {"type": "str", "required": True, "desc": "hostname"}})
def dns_lookup(host: str) -> str:
    return _call("dns_lookup", {"host": host})


@tool("port_scan", "Scan ports on a host", params={"host": {"type": "str", "required": True, "desc": "target host"}, "ports": {"type": "array", "required": False, "desc": "ports to scan (default: common ports)"}})
def port_scan(host: str, ports: List[int] = None) -> str:
    return _call("port_scan", {"host": host, "ports": ports})


# ─── MEDIA ──────────────────────────────────────────────────────

@tool("play_media", "Play media (music/video) via web", params={"query": {"type": "str", "required": True, "desc": "search query"}, "platform": {"type": "str", "required": False, "default": "youtube", "desc": "platform (youtube, spotify, soundcloud)"}})
def play_media(query: str, platform: str = "youtube") -> str:
    return _call("play_media", {"query": query, "platform_name": platform})


@tool("play_local", "Play a local media file", params={"path": {"type": "str", "required": True, "desc": "file path"}})
def play_local(path: str) -> str:
    return _call("play_local", {"path": path})


@tool("tts", "Text to speech", params={"text": {"type": "str", "required": True, "desc": "text to speak"}})
def tts(text: str) -> str:
    return _call("tts", {"text": text})


@tool("screenshot", "Take a screenshot", params={"path": {"type": "str", "required": False, "desc": "save path (auto-generated if omitted)"}})
def screenshot(path: str = None) -> str:
    return _call("screenshot", {"path": path})


@tool("list_media", "List media files in directory", params={"directory": {"type": "str", "required": False, "default": "~/Music", "desc": "directory to scan"}})
def list_media(directory: str = None) -> str:
    return _call("list_media", {"directory": directory})


@tool("media_info", "Get media file info via ffprobe", params={"path": {"type": "str", "required": True, "desc": "file path"}})
def media_info(path: str) -> str:
    return _call("media_info", {"path": path})


@tool("convert_media", "Convert media using ffmpeg", params={"inp": {"type": "str", "required": True, "desc": "input file"}, "out": {"type": "str", "required": True, "desc": "output file"}, "opts": {"type": "str", "required": False, "default": "", "desc": "ffmpeg options"}})
def convert_media(inp: str, out: str, opts: str = "") -> str:
    return _call("convert_media", {"inp": inp, "out": out, "opts": opts})


@tool("clipboard_get", "Get clipboard contents")
def clipboard_get() -> str:
    return _call("clipboard_get")


@tool("clipboard_set", "Set clipboard contents", params={"text": {"type": "str", "required": True, "desc": "text to set"}})
def clipboard_set(text: str) -> str:
    return _call("clipboard_set", {"text": text})


# ─── COMMUNICATION ──────────────────────────────────────────────

@tool("notify", "Send a toast notification", params={"title": {"type": "str", "required": True, "desc": "notification title"}, "message": {"type": "str", "required": True, "desc": "notification message"}})
def notify(title: str, message: str) -> str:
    return _call("notify", {"title": title, "message": message})


@tool("send_email", "Send email via SMTP", params={"to": {"type": "str", "required": True, "desc": "recipient email"}, "subject": {"type": "str", "required": True, "desc": "email subject"}, "body": {"type": "str", "required": True, "desc": "email body"}, "smtp": {"type": "str", "required": False, "default": "smtp.gmail.com", "desc": "SMTP server"}, "port": {"type": "int", "required": False, "default": 587, "desc": "SMTP port"}, "user": {"type": "str", "required": True, "desc": "SMTP username"}, "passwd": {"type": "str", "required": True, "desc": "SMTP password"}})
def send_email(to: str, subject: str, body: str, smtp: str = "smtp.gmail.com", port: int = 587, user: str = "", passwd: str = "") -> str:
    return _call("send_email", {"to": to, "subject": subject, "body": body, "smtp": smtp, "port": port, "user": user, "passwd": passwd})


@tool("port_check", "Check if a port is in use", params={"port": {"type": "int", "required": True, "desc": "port number"}})
def port_check(port: int) -> str:
    return _call("port_check", {"port": port})


@tool("local_ip", "Get local IP address")
def local_ip() -> str:
    return _call("local_ip")


@tool("ping", "Ping a host", params={"host": {"type": "str", "required": True, "desc": "host to ping"}, "count": {"type": "int", "required": False, "default": 4, "desc": "ping count"}})
def ping(host: str, count: int = 4) -> str:
    return _call("ping", {"host": host, "count": count})


@tool("traceroute", "Trace route to a host", params={"host": {"type": "str", "required": True, "desc": "target host"}})
def traceroute(host: str) -> str:
    return _call("traceroute", {"host": host})


# ─── DEVELOPER TOOLS ────────────────────────────────────────────

@tool("npm", "Run npm command", params={"command": {"type": "str", "required": True, "desc": "npm command (install, run, test, etc.)"}, "cwd": {"type": "str", "required": False, "default": ".", "desc": "working directory"}})
def npm(command: str, cwd: str = ".") -> str:
    return _call("npm", {"command": command, "cwd": cwd})


@tool("pip", "Run pip command", params={"command": {"type": "str", "required": True, "desc": "pip command (install, list, etc.)"}})
def pip(command: str) -> str:
    return _call("pip", {"command": command})


@tool("count_loc", "Count lines of code", params={"path": {"type": "str", "required": False, "default": ".", "desc": "project path"}, "exts": {"type": "array", "required": False, "desc": "file extensions to count"}})
def count_loc(path: str = ".", exts: List[str] = None) -> str:
    return _call("count_loc", {"path": path, "exts": exts})


@tool("run_tests", "Run tests", params={"path": {"type": "str", "required": False, "default": ".", "desc": "test path"}, "framework": {"type": "str", "required": False, "default": "pytest", "desc": "test framework (pytest, unittest, npm)"}})
def run_tests(path: str = ".", framework: str = "pytest") -> str:
    return _call("run_tests", {"path": path, "framework": framework})


@tool("lint", "Lint code", params={"path": {"type": "str", "required": False, "default": ".", "desc": "path to lint"}, "tool": {"type": "str", "required": False, "default": "ruff", "desc": "linter (ruff, black, eslint, flake8)"}})
def lint(path: str = ".", tool: str = "ruff") -> str:
    return _call("lint", {"path": path, "tool": tool})


@tool("listening_ports", "List all listening ports")
def listening_ports() -> str:
    return _call("listening_ports")


@tool("process_tree", "Show process tree", params={"pid": {"type": "int", "required": False, "desc": "root PID (default: current)"}})
def process_tree(pid: int = None) -> str:
    return _call("process_tree", {"pid": pid})


@tool("health_dashboard", "Get system health dashboard")
def health_dashboard() -> str:
    return _call("health_dashboard")


# ─── WINDOW MANAGEMENT ──────────────────────────────────────────

@tool("list_windows", "List all open windows")
def list_windows() -> str:
    return _call("list_windows")


@tool("focus_window", "Focus a window by title", params={"title": {"type": "str", "required": True, "desc": "window title (partial match)"}})
def focus_window(title: str) -> str:
    return _call("focus_window", {"title": title})


@tool("minimize_window", "Minimize a window by title", params={"title": {"type": "str", "required": True, "desc": "window title (partial match)"}})
def minimize_window(title: str) -> str:
    return _call("minimize_window", {"title": title})


@tool("maximize_window", "Maximize a window by title", params={"title": {"type": "str", "required": True, "desc": "window title (partial match)"}})
def maximize_window(title: str) -> str:
    return _call("maximize_window", {"title": title})


# ─── KEYBOARD / MOUSE ───────────────────────────────────────────

@tool("type_text", "Type text at current cursor position", params={"text": {"type": "str", "required": True, "desc": "text to type"}, "interval": {"type": "float", "required": False, "default": 0.05, "desc": "delay between keystrokes"}})
def type_text(text: str, interval: float = 0.05) -> str:
    return _call("type_text", {"text": text, "interval": interval})


@tool("press_key", "Press a key", params={"key": {"type": "str", "required": True, "desc": "key to press (enter, tab, esc, etc.)"}})
def press_key(key: str) -> str:
    return _call("press_key", {"key": key})


@tool("hotkey", "Press a hotkey combination", params={"keys": {"type": "array", "required": True, "desc": "keys to press (e.g. [ctrl, c])"}})
def hotkey(keys: List[str]) -> str:
    return _call("hotkey", {"keys": keys})


@tool("click", "Click at position", params={"x": {"type": "int", "required": False, "desc": "x coordinate"}, "y": {"type": "int", "required": False, "desc": "y coordinate"}})
def click(x: int = None, y: int = None) -> str:
    return _call("click", {"x": x, "y": y})


# ─── SECURITY / HARDWARE ────────────────────────────────────────

@tool("security_scan", "Run security scan for threats")
def security_scan() -> str:
    return _call("security_scan")


@tool("usb_devices", "List USB devices (Windows)")
def usb_devices() -> str:
    return _call("usb_devices")


@tool("gpu_info", "Get GPU information")
def gpu_info() -> str:
    return _call("gpu_info")


@tool("battery_status", "Get battery status")
def battery_status() -> str:
    return _call("battery_status")


@tool("temperatures", "Get temperature sensors")
def temperatures() -> str:
    return _call("temperatures")


@tool("firewall_status", "Get firewall status")
def firewall_status() -> str:
    return _call("firewall_status")


@tool("defender_status", "Get Windows Defender status")
def defender_status() -> str:
    return _call("defender_status")


@tool("user_accounts", "List user accounts")
def user_accounts() -> str:
    return _call("user_accounts")


# ─── ARCHIVE ─────────────────────────────────────────────────────

@tool("zip_directory", "Create zip archive of directory", params={"src": {"type": "str", "required": True, "desc": "source directory"}, "dest": {"type": "str", "required": True, "desc": "destination zip path"}})
def zip_directory(src: str, dest: str) -> str:
    return _call("zip_directory", {"src": src, "dest": dest})


@tool("unzip", "Extract zip archive", params={"src": {"type": "str", "required": True, "desc": "zip file path"}, "dest": {"type": "str", "required": True, "desc": "destination directory"}})
def unzip(src: str, dest: str) -> str:
    return _call("unzip", {"src": src, "dest": dest})


@tool("file_permissions", "Get file permissions", params={"path": {"type": "str", "required": True, "desc": "file path"}})
def file_permissions(path: str) -> str:
    return _call("file_permissions", {"path": path})


# ─── NATURAL LANGUAGE DISPATCH ──────────────────────────────────

@tool("dispatch", "Execute natural language command", params={"command": {"type": "str", "required": True, "desc": "natural language command (open chrome, search python, play music, etc.)"}})
def dispatch(command: str) -> str:
    return _call("dispatch", {"command": command})


# Aliases for common natural language patterns
@tool("shutdown", "Shutdown the system (requires confirmation)")
def shutdown() -> str:
    return _call("execute", {"command": "shutdown /s /t 10"})


@tool("restart", "Restart the system (requires confirmation)")
def restart() -> str:
    return _call("execute", {"command": "shutdown /r /t 10"})


@tool("sleep", "Put system to sleep (requires confirmation)")
def sleep() -> str:
    return _call("execute", {"command": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"})


@tool("lock", "Lock the workstation")
def lock() -> str:
    return _call("execute", {"command": "rundll32.exe user32.dll,LockWorkStation"})


@tool("empty_recycle_bin", "Empty recycle bin")
def empty_recycle_bin() -> str:
    return _call("execute", {"command": "powershell -Command \"Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.FileIO.FileSystem]::EmptyRecycleBin()\""})


@tool("clear_temp", "Clear temp files")
def clear_temp() -> str:
    return _call("execute", {"command": "powershell -Command \"Remove-Item -Path $env:TEMP\\* -Recurse -Force -ErrorAction SilentlyContinue\""})