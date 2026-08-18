import structlog
import json
import os
import time
from core.event_bus import EventBus

logger = structlog.get_logger("SATURDAY.UI")

UI_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "ui_state.json")


class WebUI:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.status = "Online"
        self.version = "1.1.0"
        self.active_connections = 0
        self.ui_state = self._load_state()
        self._notifications = []
        self._max_notifications = 100

        self.event_bus.subscribe("system_alert", self._on_system_alert)
        self.event_bus.subscribe("admin_mood_update", self._on_mood_update)
        self.event_bus.subscribe("vitals_update", self._on_vitals_update)
        self.event_bus.subscribe("voice_command", self._on_voice_command)

    def _load_state(self):
        try:
            if os.path.exists(UI_STATE_FILE):
                with open(UI_STATE_FILE, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"theme": "dark", "layout": "default", "widgets": [], "sidebar_open": True}

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(UI_STATE_FILE), exist_ok=True)
            with open(UI_STATE_FILE, "w") as f:
                json.dump(self.ui_state, f, indent=2)
        except Exception:
            pass

    def get_context(self):
        return {
            "status": self.status,
            "version": self.version,
            "active_connections": self.active_connections,
            "notifications": self._notifications[-20:],
            "ui_state": self.ui_state,
            "timestamp": time.time(),
        }

    def update_ui_state(self, updates: dict):
        if isinstance(updates, dict):
            self.ui_state.update(updates)
            self._save_state()
            self.event_bus.publish("ui_state_changed", self.ui_state)
        return self.ui_state

    def get_dashboard_data(self):
        return {
            "context": self.get_context(),
            "recent_notifications": self._notifications[-10:],
            "ui_state": self.ui_state,
        }

    def add_notification(self, title: str, message: str, level: str = "info"):
        notification = {
            "id": len(self._notifications) + 1,
            "title": title,
            "message": message,
            "level": level,
            "timestamp": time.time(),
            "read": False,
        }
        self._notifications.append(notification)
        if len(self._notifications) > self._max_notifications:
            self._notifications = self._notifications[-self._max_notifications:]
        self.event_bus.publish("ui_notification", notification)
        return notification

    def mark_notification_read(self, notification_id: int):
        for notif in self._notifications:
            if notif.get("id") == notification_id:
                notif["read"] = True
                return True
        return False

    def clear_notifications(self):
        self._notifications.clear()

    def _on_system_alert(self, data):
        alert_type = data.get("type", "system") if isinstance(data, dict) else "system"
        message = data.get("message", str(data)) if isinstance(data, dict) else str(data)
        self.add_notification("System Alert", message, level="warning")

    def _on_mood_update(self, data):
        if isinstance(data, dict):
            mood = data.get("mood", "unknown")
            score = data.get("score", 0)
            self.add_notification("Admin Mood", f"Mood: {mood} (score: {score})", level="info")

    def _on_vitals_update(self, data):
        if isinstance(data, dict) and data.get("type") == "heart_rate":
            hr = data.get("value", 0)
            if hr > 110:
                self.add_notification("Health Alert", f"Heart rate elevated: {hr} BPM", level="warning")

    def _on_voice_command(self, data):
        if isinstance(data, dict):
            cmd = data.get("command", str(data))
            self.add_notification("Voice Command", f"Received: {cmd}", level="info")
