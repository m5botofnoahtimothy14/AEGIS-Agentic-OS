from __future__ import annotations

from typing import Optional

import structlog

from . import registry

logger = structlog.get_logger("SATURDAY.Assistant.Executor")


def execute_tool(call: registry.ToolCall, fallback: Optional[str] = None) -> Optional[str]:
    """Run a registered tool and return its spoken/printed text.

    Returns None only for an unknown tool so callers can fall back to chat;
    tool exceptions are caught and turned into a safe error string.
    """
    spec = registry.get(call.name)
    if spec is None:
        logger.warning("No such tool", tool=call.name)
        return fallback
    try:
        result = spec.handler(**call.args)
        return result if isinstance(result, str) else str(result)
    except Exception as e:
        logger.exception("Tool execution failed", tool=call.name, error=str(e))
        return f"I couldn't complete that action. {e}"