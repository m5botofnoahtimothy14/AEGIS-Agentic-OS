"""Tests for AI modules: LLM engine, security assistant, predictive planner, and task automation."""

import asyncio

import pytest

from core.ai_modules.llm_engine import BuiltinBrain, LLMEngine
from core.ai_modules.predictive_planner import PredictivePlanner
from core.ai_modules.security_assistant import SecurityAssistant
from core.ai_modules.task_automation import TaskAutomator
from core.event_bus import EventBus


@pytest.fixture
def bus():
    return EventBus()


class TestBuiltinBrain:
    def test_greeting_response(self):
        brain = BuiltinBrain()
        result = brain.respond("hello saturday")
        assert len(result) > 0

    def test_time_response(self):
        brain = BuiltinBrain()
        result = brain.respond("what time is it")
        assert "It's" in result

    def test_thanks_response(self):
        brain = BuiltinBrain()
        result = brain.respond("thank you")
        assert len(result) > 0

    def test_joke_contains_joke_content(self):
        brain = BuiltinBrain()
        result = brain.respond("tell me a joke")
        assert "programmer" in result or "SQL" in result or "JavaScript" in result or "binary" in result

    def test_context_is_recorded(self):
        brain = BuiltinBrain()
        brain.respond("the quick brown fox jumps over the lazy dog")
        assert len(brain.context) >= 1


class TestLLMEngine:
    def test_engine_uses_builtin_brain_by_default(self):
        engine = LLMEngine()
        assert engine.available is True
        assert engine._use_builtin is True

    def test_chat_returns_nonempty_string(self):
        engine = LLMEngine()

        async def run():
            return await engine.chat("hello")

        result = asyncio.run(run())
        assert isinstance(result, str)
        assert len(result) > 0

    def test_chat_stream_yields_tokens(self):
        engine = LLMEngine()

        async def collect():
            chunks = []
            async for chunk in engine.chat_stream("hello saturday"):
                chunks.append(chunk)
            return "".join(chunks)

        result = asyncio.run(collect())
        assert len(result) > 0


class TestSecurityAssistant:
    def test_scan_request_publishes_response(self, bus):
        received = []
        bus.subscribe("voice_response", lambda text: received.append(text))
        SecurityAssistant(bus, ai_engine=None)
        bus.publish("voice_command", "scan network")
        assert received, "expected a voice_response for security scan command"


class TestPredictivePlanner:
    def test_update_plan_with_numeric_values_publishes_prediction(self, bus):
        predictions = []
        bus.subscribe("prediction", lambda data: predictions.append(data))
        planner = PredictivePlanner(bus)
        result = planner.update_plan({"values": [10, 12, 14, 16]})
        assert result["plan_count"] == 1
        assert predictions, "expected a prediction event for trending values"
        assert predictions[0]["trend"] == 2.0

    def test_update_plan_no_values_is_safe(self, bus):
        planner = PredictivePlanner(bus)
        result = planner.update_plan({"something": "else"})
        assert result["plan_count"] == 1


class TestTaskAutomator:
    def test_flag_transitions(self, bus):
        automator = TaskAutomator(bus)
        assert automator.running is False

        # start() is an infinite loop; we flip the flag directly to test the lifecycle.
        automator.running = True
        assert automator.running is True

        async def stop_cycle():
            await automator.stop()
            return automator.running

        assert asyncio.run(stop_cycle()) is False
