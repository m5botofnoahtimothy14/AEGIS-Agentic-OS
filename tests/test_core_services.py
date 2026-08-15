"""Tests for core runtime, state, config, and RBAC services."""

import json
import threading
import time

import pytest

from core.config import ConfigManager
from core.rbac import RBAC
from core.runtime import RuntimeStats
from core.state import SystemState


@pytest.fixture
def isolated_state(tmp_path):
    """Point SystemState at a temp state file to avoid touching the repo copy."""
    state_file = tmp_path / "state.json"

    class FakeState(SystemState):
        def __init__(self):
            # Inherit the working RLock from SystemState.
            self.lock = threading.RLock()
            self.state_file = str(state_file)
            self.config = ConfigManager()
            self.state = {
                "user_mode": "Sir",
                "aeigis_active": True,
                "edith_active": True,
                "homebot_connected": False,
                "cloud_session": False,
                "last_command": None,
                "security_alerts": [],
                "active_modules": [],
            }
            self.load_state()

    return FakeState()


class TestRuntimeStats:
    def test_uptime_increases(self):
        runtime = RuntimeStats()
        time.sleep(0.05)
        assert runtime.get_uptime() >= 0.05

    def test_resource_usage_shape(self):
        runtime = RuntimeStats()
        usage = runtime.get_resource_usage()
        assert "memory_mb" in usage
        assert "cpu_percent" in usage
        assert "uptime_sec" in usage
        assert usage["memory_mb"] > 0


class TestSystemState:
    def test_default_user_mode(self, isolated_state):
        assert isolated_state.get_state("user_mode") == "Sir"

    def test_update_and_get_state(self, isolated_state):
        isolated_state.update_state("last_command", "hello saturday")
        assert isolated_state.get_state("last_command") == "hello saturday"

    def test_state_persists_to_disk(self, isolated_state):
        isolated_state.update_state("homebot_connected", True)
        with open(isolated_state.state_file) as handle:
            data = json.load(handle)
        assert data["homebot_connected"] is True

    def test_append_to_list(self, isolated_state):
        isolated_state.append_to_list("active_modules", "voice")
        isolated_state.append_to_list("active_modules", "vision")
        assert isolated_state.get_state("active_modules") == ["voice", "vision"]

    def test_missing_key_returns_default(self, isolated_state):
        assert isolated_state.get_state("does_not_exist", "fallback") == "fallback"


class TestConfigManager:
    def test_get_nested_key(self):
        config = ConfigManager()
        assert config.get("security.cpu_threshold") == 85

    def test_get_missing_key_returns_default(self):
        config = ConfigManager()
        assert config.get("missing.path", "default-value") == "default-value"

    def test_set_and_get(self):
        config = ConfigManager()
        config.set("test.nested.value", "hello")
        assert config.get("test.nested.value") == "hello"


class TestRBAC:
    def test_sir_has_all_modules(self, isolated_state):
        rbac = RBAC(isolated_state)
        assert rbac.can_execute("all_modules") is True
        assert rbac.can_execute("homebot_control") is True

    def test_guest_denied_privileged_modules(self, isolated_state):
        rbac = RBAC(isolated_state)
        rbac.set_user_mode("guest")
        assert rbac.can_execute("homebot_control") is False
        assert rbac.can_execute("read_only") is True

    def test_set_user_mode_persists(self, isolated_state):
        rbac = RBAC(isolated_state)
        rbac.set_user_mode("Noah")
        assert isolated_state.get_state("user_mode") == "Noah"
