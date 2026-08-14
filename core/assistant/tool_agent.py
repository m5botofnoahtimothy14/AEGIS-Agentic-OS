from __future__ import annotations

import json
import re
from typing import Optional

import structlog

from . import registry

logger = structlog.get_logger("SATURDAY.Assistant.ToolAgent")

ACTION_VERBS = (
    "open ",
    "launch ",
    "start ",
    "run ",
    "play ",
    "close ",
    "shut ",
    "kill ",
    "stop ",
    "create ",
    "write ",
    "save ",
    "remember ",
    "remind ",
    "set a reminder",
    "increase ",
    "decrease ",
    "raise ",
    "lower ",
    "turn up ",
    "turn down ",
    "mute ",
    "unmute ",
    "volume ",
)

_GATE_MAX_WORDS = 6


def _looks_like_action(query: str) -> bool:
    q = query.strip().lower()
    if any(q.startswith(v) or f" {v}" in f" {q}" for v in ACTION_VERBS):
        return True
    words = set(re.findall(r"[a-z0-9]+", q))
    if len(words) > _GATE_MAX_WORDS:
        return False
    for spec in registry.all_tools():
        if words & set(spec.name.lower().split("_")):
            return True
    return False


def _tool_list_text() -> str:
    lines = []
    for index, spec in enumerate(registry.all_tools(), start=1):
        if spec.params:
            param_lines = [
                f"     - {pname} ({pspec.type}, {'required' if pspec.required else 'optional'}): {pspec.desc}"
                for pname, pspec in spec.params.items()
            ]
            params_text = "\n   params:\n" + "\n".join(param_lines)
        else:
            params_text = "\n   params: none"
        lines.append(f"{index}. {spec.name}\n   - {spec.description}{params_text}")
    return "\n\n".join(lines)


def _extract_first_json(text: str) -> Optional[dict]:
    text = text.replace("```json", "").replace("```", "")
    start = text.find("{")
    if start == -1:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
        return obj
    except json.JSONDecodeError:
        return None


def _build_call_from_parsed(parsed: dict) -> Optional[registry.ToolCall]:
    name = (parsed.get("tool") or "none").strip().lower()
    if name in ("", "none", "null"):
        return None
    spec = registry.get(name)
    if spec is None:
        logger.info("Tool agent picked an unknown tool; falling back to chat", tool=name)
        return None
    raw_args = parsed.get("args", {})
    if not isinstance(raw_args, dict):
        raw_args = {}
    args, error = registry.coerce_and_validate(spec, raw_args)
    if error:
        logger.info("Tool agent arg error; falling back to chat", tool=name, error=error)
        return None
    return registry.ToolCall(name=name, args=args)


async def decide_tool(query: str, llm=None, raw_query: Optional[str] = None) -> Optional[registry.ToolCall]:
    """Ask the configured LLM to map an action-shaped request to one tool.

    Only fires for command-looking phrases (action-verb gate); returns None
    for questions/conversation. Uses the SATURDAY LLMEngine so it works with
    Ollama, llama-cpp, or the built-in brain (builtin can't produce JSON, so it
    safely falls back to chat).
    """
    if llm is None or not _looks_like_action(query):
        return None
    if raw_query is None:
        raw_query = query
    prompt = f"""You are a strict tool selector for SATURDAY. Map the user's
request to exactly one of the available tools, OR return "none" if the request
is not an explicit command to perform one of these actions.

Available tools:
{_tool_list_text()}

Strict rules:
- Output ONE JSON object only. No prose, no markdown.
- Shape: {{"tool": "<name>", "args": {{...}}}}  OR  {{"tool": "none"}}.
- Fill "args" using the tool's declared params; take values from the user's words.
- Only choose a tool if the user is explicitly asking to perform it now.
- Questions, explanations, conversation, anything with "what"/"why"/"how"/
  "explain"/"tell me"/"describe" -> {{"tool": "none"}}.
- If unsure, return {{"tool": "none"}}.

Examples:
- "remember that i like coffee" -> {{"tool": "remember", "args": {{"fact": "i like coffee"}}}}
- "create a note about the meeting" -> {{"tool": "create_note", "args": {{"title": "note about the meeting"}}}}
- "what is python" -> {{"tool": "none"}}

User Request:
{raw_query}

JSON:"""
    try:
        text = await llm.chat(prompt)
    except Exception as e:
        logger.warning("Tool agent LLM call failed", error=str(e))
        return None
    parsed = _extract_first_json(text)
    if parsed is None:
        logger.debug("Tool agent returned no JSON; falling back to chat")
        return None
    return _build_call_from_parsed(parsed)