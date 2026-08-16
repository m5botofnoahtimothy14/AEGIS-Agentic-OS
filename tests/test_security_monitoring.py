"""Tests for security, monitoring, and self-healing modules."""

import asyncio
import json
import os

import pytest

from core.admin_mood import AdminMood
from core.alert_manager import AlertManager
from core.antivirus import Antivirus
from core.audit import AuditLogger
from core.cyber_defense import CyberDefense
from core.event_bus import EventBus
from core.malware_guard import MalwareGuard
from core.security import SecurityMonitor
from core.self_heal import HealingNeuralNetwork


@pytest.fixture
def bus():
    return EventBus()


class TestSecurityMonitor:
    def test_monitor_starts(self, bus):
        monitor = SecurityMonitor(bus)
        assert monitor.monitoring is False
        monitor.start_monitoring()
        assert monitor.monitoring is True
        monitor.monitoring = False  # stop loop


class TestAntivirus:
    def test_hash_file(self, tmp_path):
        av = Antivirus(scan_paths=[], quarantine_folder=str(tmp_path / "quarantine"))
        target = tmp_path / "sample.txt"
        target.write_text("SATURDAY test content", encoding="utf-8")
        digest = av.hash_file(str(target))
        assert len(digest) == 64  # sha256 hex
        assert digest.isalnum()

    def test_quarantine_moves_file(self, tmp_path):
        quarantine = tmp_path / "quarantine"
        av = Antivirus(scan_paths=[], quarantine_folder=str(quarantine))
        target = tmp_path / "flagged.bin"
        target.write_bytes(b"not-safe")
        av.quarantine(str(target))
        assert not target.exists()
        assert (quarantine / "flagged.bin").exists()

    def test_start_sets_running(self, tmp_path):
        av = Antivirus(scan_paths=[], quarantine_folder=str(tmp_path / "q"))
        av.start(interval=3600)
        assert av.running is True
        av.running = False


class TestMalwareGuard:
    def test_scan_core_files_hashes_python_files(self, bus):
        guard = MalwareGuard(bus)
        guard.scan_core_files()
        assert len(guard.file_hashes) > 0

    def test_monitor_processes_returns_list(self, bus):
        guard = MalwareGuard(bus)

        async def run():
            return await guard.monitor_processes()

        result = asyncio.run(run())
        assert isinstance(result, list)


class TestCyberDefense:
    def test_activate_and_handle_alert(self, bus):
        defense = CyberDefense(bus)
        assert defense.active is False
        defense.activate()
        assert defense.active is True
        defense.active = False  # stop loop
        # handler must not raise
        defense.handle_alert({"type": "test", "value": 1})


class TestAuditLogger:
    def test_log_appends_entry(self, tmp_path, monkeypatch):
        log_file = tmp_path / "audit.json"
        fake_state = object()

        class FakeAudit(AuditLogger):
            def __init__(self):
                self.state = fake_state
                self.audit_file = str(log_file)
                self.lock = __import__("threading").Lock()
                self.audit_log = []
                if os.path.exists(self.audit_file):
                    with open(self.audit_file, "r") as handle:
                        self.audit_log = json.load(handle)

        logger = FakeAudit()
        logger.log("Sir", "execute_command", module="homebot", details={"cmd": "forward"})

        assert len(logger.audit_log) == 1
        entry = logger.audit_log[0]
        assert entry["user"] == "Sir"
        assert entry["action"] == "execute_command"
        assert entry["module"] == "homebot"


class TestAdminMood:
    def test_response_to_voice_command_raises_score(self, bus):
        mood = AdminMood(bus)
        initial = mood.score
        bus.publish("voice_command", "hello saturday")
        assert mood.score > initial

    def test_system_alert_lowers_score(self, bus):
        mood = AdminMood(bus)
        initial = mood.score
        bus.publish("system_alert", {"message": "test"})
        assert mood.score < initial

    def test_mood_labels(self, bus):
        mood = AdminMood(bus)
        mood.score = -8
        mood._update("test")
        assert mood.mood == "critical"
        mood.score = 6
        mood._update("test")
        assert mood.mood == "happy"


class TestAlertManager:
    def test_loud_noise_publishes_voice_response(self, bus):
        received = []
        bus.subscribe("voice_response", lambda text: received.append(text))
        AlertManager(bus)
        bus.publish("loud_noise", {"db": 90})
        assert received, "expect a voice_response after loud_noise"

    def test_health_alert_threshold(self, bus):
        received = []
        bus.subscribe("voice_response", lambda text: received.append(text))
        AlertManager(bus)
        bus.publish("health_update", {"cpu": 95, "memory": 95})
        assert received, "expect voice_response for high resource usage"


class TestHealingNeuralNetwork:
    def test_predict_healing_returns_actions(self):
        nn = HealingNeuralNetwork()
        import numpy as np

        features = np.zeros((1, 15))
        features[0, 0] = 0.9  # high cpu signal
        actions = nn.predict_healing(features)
        assert isinstance(actions, list)
        assert len(actions) >= 1
        assert all(isinstance(item, tuple) and len(item) == 2 for item in actions)

    def test_learn_from_outcome_does_not_raise(self):
        nn = HealingNeuralNetwork()
        import numpy as np

        features = np.random.rand(1, 15)
        nn.learn_from_outcome(features, "monitor_only", success=True)
