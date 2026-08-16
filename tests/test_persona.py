"""Tests for the dual-AI persona manager (SATURDAY / EDITH)."""

from core.persona import PersonaManager, get_persona_manager


def test_persona_manager_has_saturday_and_edith():
    manager = PersonaManager()
    assert "SATURDAY" in manager.personas
    assert "EDITH" in manager.personas
    assert manager.active.name == "SATURDAY"


def test_activate_switches_persona():
    manager = PersonaManager()
    manager.activate("EDITH")
    assert manager.active_name == "EDITH"
    manager.activate("saturday")
    assert manager.active_name == "SATURDAY"


def test_detect_target_routing():
    manager = PersonaManager()
    assert manager.detect_target("edith, open the door") == "EDITH"
    assert manager.detect_target("saturday status check") == "SATURDAY"
    manager.activate("EDITH")
    assert manager.detect_target("what's the weather?") == "EDITH"


def test_route_returns_matching_persona():
    manager = PersonaManager()
    persona = manager.route("edith please help")
    assert persona.name == "EDITH"
    assert manager.active_name == "EDITH"


def test_persona_describe_has_voice_and_role():
    manager = PersonaManager()
    saturday_desc = manager.persona_for("SATURDAY").describe()
    assert saturday_desc["name"] == "SATURDAY"
    assert saturday_desc["role"] == "primary"
    edith_desc = manager.persona_for("EDITH").describe()
    assert edith_desc["role"] == "subdomain"


def test_build_prompt_includes_system_prompt_and_input():
    manager = PersonaManager()
    prompt = manager.build_prompt("hello SATURDAY")
    assert "SATURDAY" in prompt
    assert "User input: hello SATURDAY" in prompt


def test_status_shape():
    manager = PersonaManager()
    status = manager.status()
    assert status["active"] in ("SATURDAY", "EDITH")
    assert status["primary"] == "SATURDAY"
    assert set(status["personas"].keys()) == {"SATURDAY", "EDITH"}


def test_singleton_getter():
    assert get_persona_manager() is get_persona_manager()
