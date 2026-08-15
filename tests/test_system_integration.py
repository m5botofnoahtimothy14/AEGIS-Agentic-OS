"""Whole-system integration test: verifies the complete SATURDAY stack boots and runs."""

import asyncio
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestSystemBootstrap:
    def test_cli_agent_runs(self):
        """The saturday_agent_cli entry point must produce output."""
        result = subprocess.run(
            [sys.executable, "saturday_agent_cli.py", "what can you do"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        assert result.stdout.strip().startswith("I am SATURDAY")

    def test_cli_json_output(self):
        """The agent CLI --json flag must produce valid JSON."""
        result = subprocess.run(
            [sys.executable, "saturday_agent_cli.py", "--json", "status report"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["mode"] == "offline"
        assert "message" in payload

    def test_production_runner_importable(self):
        import run_production

        assert callable(run_production.main)

    def test_api_gateway_importable(self):
        import api_gateway

        assert api_gateway.app is not None
        assert hasattr(api_gateway, "execute_command")

    def test_simple_mqtt_broker_importable(self):
        import simple_mqtt_broker

        assert hasattr(simple_mqtt_broker, "main") or hasattr(simple_mqtt_broker, "SimpleMQTTBroker")


class TestCoreImportSurface:
    """Import every core module to catch broken imports across the system."""

    CORE_MODULES = [
        "core.main",
        "core.event_bus",
        "core.ai_agent",
        "core.runtime",
        "core.state",
        "core.config",
        "core.rbac",
        "core.persona",
        "core.task_manager",
        "core.brain",
        "core.security",
        "core.antivirus",
        "core.malware_guard",
        "core.cyber_defense",
        "core.audit",
        "core.admin_mood",
        "core.alert_manager",
        "core.greeting",
        "core.self_heal",
        "core.self_healing",
        "core.self_rewrite",
        "core.system_monitor",
        "core.system_tray",
        "core.sound_monitor",
        "core.spatial_audio",
        "core.voice_chat",
        "core.voice_command_system",
        "core.learning_manager",
        "core.pipeline",
        "core.engagement",
        "core.usb_watchdog",
        "core.remote_desktop",
        "core.window_manager",
        "core.agent_service",
        "core.ai_modules.llm_engine",
        "core.ai_modules.security_assistant",
        "core.ai_modules.predictive_planner",
        "core.ai_modules.task_automation",
        "core.ai_modules.code_review",
        "core.ai_modules.code_writer",
        "core.ai_modules.issue_handler",
        "core.assistant.builtins",
        "core.assistant.executor",
        "core.assistant.loader",
        "core.assistant.memory",
        "core.assistant.offline_llm",
        "core.assistant.profile",
        "core.assistant.registry",
        "core.assistant.reminders",
        "core.assistant.router",
        "core.assistant.tool_agent",
        "core.assistant",
    ]

    @pytest.mark.parametrize("module_name", CORE_MODULES)
    def test_module_imports(self, module_name):
        module = importlib.import_module(module_name)
        assert module is not None


class TestFastAPIApp:
    def test_fastapi_app_imports(self):
        """The FastAPI app must import without raising."""
        from core.main import app

        assert app.title == "SATURDAY AI OS"

    def test_app_has_status_route_table(self):
        from core.main import app

        paths = {
            getattr(route, "path", None)
            for route in app.routes
        }
        # Routes defined at import time (before the core startup hook runs).
        assert "/api/debug" in paths
        assert "/ws/events" in paths
        assert "/agent" in paths


class TestEndToEndAgentPipeline:
    def test_full_agent_workflow(self, tmp_path):
        """Run a realistic multi-step agent workflow."""
        from core.ai_agent import AIAgent, OfflineAIAgent

        # AIAgent is a process-wide singleton; verify it accepts kwargs now.
        singleton = AIAgent(storage_dir=str(tmp_path))
        assert singleton is not None

        # OfflineAIAgent supports per-instance storage directories.
        agent = OfflineAIAgent(storage_dir=str(tmp_path))

        # 1. Information intent
        info = agent.process_command("what can you do")
        assert info["mode"] == "offline"
        assert info["intent"] == "info"

        # 2. Memory intent
        memory = agent.process_command("remember that I like robotics")
        assert memory["action"] == "remember"

        # 3. Status intent
        status = agent.process_command("system status")
        assert status["intent"] == "status"

        # 4. Task creation
        task = agent.process_command("create task verify end to end flow")
        assert task["action"] == "task"

        # 5. Notes
        note = agent.process_command("write note whole system works")
        assert note["action"] == "file"

        # 6. Persistence across instances
        agent.save_state()
        reloaded = OfflineAIAgent(storage_dir=str(tmp_path))
        assert reloaded.memory["facts"] or reloaded.memory["preferences"].get("likes")


class TestAgentServiceApp:
    def test_agent_service_creates_fastapi_app(self):
        from core.agent_service import create_agent_app

        agent_app = create_agent_app()
        assert agent_app is not None
        assert list(agent_app.routes)
