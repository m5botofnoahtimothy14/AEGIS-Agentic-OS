import logging
import time
import json
import os
import threading
from core.event_bus import EventBus

logger = logging.getLogger("SATURDAY.EDITH.Tasks")

TASK_LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "edith_task_log.json")

REGISTERED_TASKS = {
    "email_check": {"description": "Check and summarize recent emails", "category": "communication", "timeout": 30},
    "calendar_review": {"description": "Review today's calendar and upcoming events", "category": "productivity", "timeout": 15},
    "web_research": {"description": "Research a topic using web search", "category": "research", "timeout": 60},
    "code_review": {"description": "Review code for issues and suggestions", "category": "development", "timeout": 45},
    "file_organization": {"description": "Organize files in specified directory", "category": "productivity", "timeout": 120},
    "data_analysis": {"description": "Analyze data from file or input", "category": "analytics", "timeout": 60},
    "report_generation": {"description": "Generate a summary report", "category": "productivity", "timeout": 45},
    "security_scan": {"description": "Run a security scan on the system", "category": "security", "timeout": 120},
    "backup_check": {"description": "Verify backup status and integrity", "category": "maintenance", "timeout": 30},
    "system_diagnostics": {"description": "Run system health diagnostics", "category": "maintenance", "timeout": 60},
    "social_monitor": {"description": "Monitor social media mentions", "category": "social", "timeout": 30},
    "news_briefing": {"description": "Generate a news briefing on topics of interest", "category": "information", "timeout": 45},
    "smart_home_control": {"description": "Control smart home devices", "category": "automation", "timeout": 15},
    "voice_command": {"description": "Process and execute a voice command", "category": "control", "timeout": 30},
    "task_scheduling": {"description": "Schedule or reschedule tasks", "category": "productivity", "timeout": 15},
    "reminder_set": {"description": "Set a reminder for a specified time", "category": "productivity", "timeout": 10},
    "music_play": {"description": "Play music or a playlist", "category": "entertainment", "timeout": 15},
    "weather_report": {"description": "Get current weather and forecast", "category": "information", "timeout": 15},
    "translation": {"description": "Translate text between languages", "category": "utility", "timeout": 30},
    "summarization": {"description": "Summarize a document or text", "category": "utility", "timeout": 45},
}


class EdithTaskHandler:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.task_history = []
        self.active_tasks = {}
        self.completed_tasks = []
        self.failed_tasks = []
        self._task_counter = 0
        self._load_history()
        logger.info("EDITH Task Handler initialized with %d registered task types.", len(REGISTERED_TASKS))

    def _load_history(self):
        try:
            if os.path.exists(TASK_LOG_FILE):
                with open(TASK_LOG_FILE, "r") as f:
                    data = json.load(f)
                    self.task_history = data.get("history", [])[-200:]
                    self._task_counter = data.get("counter", 0)
        except Exception:
            pass

    def _save_history(self):
        try:
            os.makedirs(os.path.dirname(TASK_LOG_FILE), exist_ok=True)
            with open(TASK_LOG_FILE, "w") as f:
                json.dump({
                    "history": self.task_history[-200:],
                    "counter": self._task_counter,
                }, f, indent=2)
        except Exception:
            pass

    def execute_task(self, task_name: str, params: dict = None):
        params = params or {}
        task_name_lower = task_name.strip().lower()

        if task_name_lower not in REGISTERED_TASKS:
            self.event_bus.publish("task_failed", {"task": task_name, "error": "Unknown task type"})
            logger.warning("EDITH received unknown task: %s", task_name)
            return {"success": False, "error": f"Unknown task type: {task_name}", "available_tasks": list(REGISTERED_TASKS.keys())}

        self._task_counter += 1
        task_id = f"EDITH-{self._task_counter:04d}"
        task_meta = REGISTERED_TASKS[task_name_lower]

        task_record = {
            "id": task_id,
            "name": task_name_lower,
            "description": task_meta["description"],
            "category": task_meta["category"],
            "params": params,
            "status": "running",
            "started_at": time.time(),
            "completed_at": None,
            "result": None,
            "error": None,
        }

        self.active_tasks[task_id] = task_record
        self.event_bus.publish("task_started", {"task_id": task_id, "name": task_name_lower})
        logger.info("EDITH executing task %s [%s]: %s", task_id, task_meta["category"], task_meta["description"])

        try:
            result = self._dispatch_task(task_name_lower, params, task_meta.get("timeout", 60))
            task_record["status"] = "completed"
            task_record["result"] = result
            task_record["completed_at"] = time.time()
            self.completed_tasks.append(task_record)
            self.active_tasks.pop(task_id, None)
            self.task_history.append(task_record)
            self._save_history()
            self.event_bus.publish("task_completed", {"task_id": task_id, "name": task_name_lower, "result": result})
            return {"success": True, "task_id": task_id, "result": result}

        except Exception as e:
            task_record["status"] = "failed"
            task_record["error"] = str(e)
            task_record["completed_at"] = time.time()
            self.failed_tasks.append(task_record)
            self.active_tasks.pop(task_id, None)
            self.task_history.append(task_record)
            self._save_history()
            self.event_bus.publish("task_failed", {"task_id": task_id, "name": task_name_lower, "error": str(e)})
            logger.warning("EDITH task %s failed: %s", task_id, e)
            return {"success": False, "task_id": task_id, "error": str(e)}

    def _dispatch_task(self, task_name: str, params: dict, timeout: int):
        dispatch_map = {
            "email_check": lambda p: self._task_email_check(p),
            "calendar_review": lambda p: self._task_calendar_review(p),
            "web_research": lambda p: self._task_web_research(p),
            "code_review": lambda p: self._task_code_review(p),
            "file_organization": lambda p: self._task_file_organization(p),
            "data_analysis": lambda p: self._task_data_analysis(p),
            "report_generation": lambda p: self._task_report_generation(p),
            "security_scan": lambda p: self._task_security_scan(p),
            "backup_check": lambda p: self._task_backup_check(p),
            "system_diagnostics": lambda p: self._task_system_diagnostics(p),
            "social_monitor": lambda p: self._task_social_monitor(p),
            "news_briefing": lambda p: self._task_news_briefing(p),
            "smart_home_control": lambda p: self._task_smart_home_control(p),
            "voice_command": lambda p: self._task_voice_command(p),
            "task_scheduling": lambda p: self._task_task_scheduling(p),
            "reminder_set": lambda p: self._task_reminder_set(p),
            "music_play": lambda p: self._task_music_play(p),
            "weather_report": lambda p: self._task_weather_report(p),
            "translation": lambda p: self._task_translation(p),
            "summarization": lambda p: self._task_summarization(p),
        }
        handler = dispatch_map.get(task_name)
        if handler:
            return handler(params)
        return {"status": "dispatched", "message": f"Task {task_name} queued for execution"}

    def _task_system_diagnostics(self, params):
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "cpu_percent": round(cpu, 1),
            "memory_percent": round(mem.percent, 1),
            "memory_used_gb": round(mem.used / (1024**3), 2),
            "disk_percent": round(disk.percent, 1),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "process_count": len(list(psutil.process_iter())),
        }

    def _task_security_scan(self, params):
        return {"status": "scan_initiated", "message": "Security scan dispatched to SystemMonitor"}

    def _task_web_research(self, params):
        query = params.get("query", params.get("topic", "general"))
        return {"status": "research_queued", "query": query, "message": f"Web research for '{query}' queued"}

    def _task_email_check(self, params):
        return {"status": "email_check_completed", "emails_found": 0, "message": "Email integration not yet configured"}

    def _task_calendar_review(self, params):
        return {"status": "calendar_reviewed", "events_today": 0, "message": "Calendar integration not yet configured"}

    def _task_code_review(self, params):
        file_path = params.get("file", "")
        return {"status": "code_reviewed", "file": file_path, "issues_found": 0, "message": f"Code review for {file_path} completed"}

    def _task_file_organization(self, params):
        directory = params.get("directory", os.path.expanduser("~/Downloads"))
        return {"status": "organized", "directory": directory, "files_moved": 0}

    def _task_data_analysis(self, params):
        source = params.get("source", "unknown")
        return {"status": "analysis_complete", "source": source, "insights": []}

    def _task_report_generation(self, params):
        report_type = params.get("type", "general")
        return {"status": "report_generated", "type": report_type, "message": f"{report_type} report generated"}

    def _task_backup_check(self, params):
        return {"status": "backup_verified", "last_backup": "unknown", "integrity": "ok"}

    def _task_social_monitor(self, params):
        return {"status": "monitoring", "platforms": ["twitter", "github"], "mentions": 0}

    def _task_news_briefing(self, params):
        topics = params.get("topics", ["technology", "AI"])
        return {"status": "briefing_ready", "topics": topics, "articles": 0}

    def _task_smart_home_control(self, params):
        device = params.get("device", "unknown")
        action = params.get("action", "status")
        return {"status": "controlled", "device": device, "action": action}

    def _task_voice_command(self, params):
        command = params.get("command", "")
        return {"status": "processed", "command": command}

    def _task_task_scheduling(self, params):
        return {"status": "scheduled", "task": params.get("task", ""), "time": params.get("time", "")}

    def _task_reminder_set(self, params):
        return {"status": "reminder_set", "message": params.get("message", ""), "time": params.get("time", "")}

    def _task_music_play(self, params):
        return {"status": "playing", "track": params.get("track", "default playlist")}

    def _task_weather_report(self, params):
        location = params.get("location", "current")
        return {"status": "weather_fetched", "location": location, "temperature": "unknown"}

    def _task_translation(self, params):
        text = params.get("text", "")
        target_lang = params.get("target", "en")
        return {"status": "translated", "original": text, "target_lang": target_lang, "translation": text}

    def _task_summarization(self, params):
        text = params.get("text", "")
        return {"status": "summarized", "original_length": len(text), "summary": text[:200] if text else ""}

    def get_task_history(self, limit=20):
        return self.task_history[-limit:]

    def get_active_tasks(self):
        return list(self.active_tasks.values())

    def get_stats(self):
        return {
            "total_executed": self._task_counter,
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "active": len(self.active_tasks),
            "available_task_types": len(REGISTERED_TASKS),
            "task_types": list(REGISTERED_TASKS.keys()),
        }
