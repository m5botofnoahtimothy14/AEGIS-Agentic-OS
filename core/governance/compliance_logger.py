import json
import time
import os
import threading
from pathlib import Path

class ComplianceLogger:
    def __init__(self, log_dir="logs/compliance"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "events.jsonl"
        self.lock = threading.Lock()
        self.metrics = {"events_logged": 0, "errors": 0, "categories": {}}
        self._setup_rotation()

    def _setup_rotation(self):
        # Rotate logs larger than 10MB or older than 30 days
        try:
            if self.log_file.exists():
                size_mb = self.log_file.stat().st_size / (1024 * 1024)
                if size_mb > 10:
                    timestamp = int(time.time())
                    archive = self.log_dir / f"events_{timestamp}.jsonl"
                    self.log_file.rename(archive)
        except Exception as e:
            logger = __import__("structlog").get_logger("SATURDAY.Compliance")
            logger.warning(f"Rotation setup error: {e}")

    def log_event(self, event_type, details):
        try:
            entry = {
                "timestamp": time.time(),
                "event_type": event_type,
                "details": details
            }
            with self.lock:
                with open(self.log_file, "a") as f:
                    f.write(json.dumps(entry) + "\n")
                self.metrics["events_logged"] += 1
                cat = details.get("category", "unknown")
                self.metrics["categories"][cat] = self.metrics["categories"].get(cat, 0) + 1
        except Exception as e:
            import structlog
            logger = structlog.get_logger("SATURDAY.Compliance")
            logger.error("compliance_log_error", error=str(e))
            self.metrics["errors"] += 1
        return True

    def get_metrics(self):
        return dict(self.metrics)

    def get_recent_events(self, n=50):
        events = []
        try:
            if self.log_file.exists():
                with open(self.log_file, "r") as f:
                    lines = f.readlines()
                    events = [json.loads(line) for line in lines[-n:]]
        except Exception as e:
            import structlog
            logger = structlog.get_logger("SATURDAY.Compliance")
            logger.warning(f"Failed to read recent events: {e}")
        return events