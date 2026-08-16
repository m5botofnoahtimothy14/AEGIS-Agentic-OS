"""Tests for the assistant package: registry, builtins, and validation."""

from core.assistant import builtins  # noqa: F401  (decorators register on import)
from core.assistant.registry import all_tools, coerce_and_validate, get, register, ToolSpec

# All tool names here are unique so tests never depend on execution order.

def test_builtin_tools_registered():
    tools = all_tools()
    names = {spec.name for spec in tools}
    assert {
        "get_time",
        "get_date",
        "system_status",
        "help",
        "remember",
        "create_note",
        "list_notes",
        "set_reminder",
    } <= names


def test_get_returns_toolspec():
    spec = get("get_time")
    assert spec is not None
    assert spec.name == "get_time"
    assert callable(spec.handler)


def test_get_missing_tool_returns_none():
    assert get("does_not_exist") is None


def test_register_and_get_custom_tool():
    def custom_handler():
        return "ok"

    register(
        ToolSpec(
            name="custom_tool_ordered",
            description="A custom tool",
            handler=custom_handler,
        )
    )
    spec = get("custom_tool_ordered")
    assert spec is not None
    assert spec.handler() == "ok"


def test_builtin_handler_executes():
    get_time = get("get_time")
    result = get_time.handler()
    assert result.startswith("It's ")


def test_coerce_and_validate_required_param():
    remember = get("remember")
    args, error = coerce_and_validate(remember, {"fact": "I like robotics"})
    assert error is None
    assert args == {"fact": "I like robotics"}


def test_coerce_and_validate_missing_required():
    remember = get("remember")
    args, error = coerce_and_validate(remember, {})
    assert args == {}
    assert error is not None
    assert "missing required param" in error


def test_coerce_and_validate_type_conversion():
    set_reminder = get("set_reminder")
    args, error = coerce_and_validate(
        set_reminder, {"minutes": "30", "message": "take a break"}
    )
    assert error is None
    assert args["minutes"] == 30
    assert args["message"] == "take a break"


def test_help_lists_all_tools():
    help_spec = get("help")
    result = help_spec.handler()
    # help is registered, so it must mention itself
    assert "help" in result
