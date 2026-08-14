from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

logger = structlog.get_logger("SATURDAY.Assistant.Registry")


@dataclass(frozen=True)
class ParamSpec:
    type: str = "str"
    required: bool = True
    desc: str = ""
    default: Any = None


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    params: Dict[str, ParamSpec] = field(default_factory=dict)
    handler: Callable = None

    def __post_init__(self):
        if self.handler is None:
            raise ValueError(f"Tool {self.name!r} must declare a handler")


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: Dict[str, Any] = field(default_factory=dict)


_REGISTRY: Dict[str, ToolSpec] = {}

_ORDER: list[str] = []


def register(spec: ToolSpec) -> None:
    if spec.name in _REGISTRY:
        logger.warning(f"Tool {spec.name!r} re-registered; overwriting")
    else:
        _ORDER.append(spec.name)
    _REGISTRY[spec.name] = spec


def get(name: str) -> Optional[ToolSpec]:
    return _REGISTRY.get(name)


def all_tools() -> list[ToolSpec]:
    return [_REGISTRY[name] for name in _ORDER if name in _REGISTRY]


def clear() -> None:
    _REGISTRY.clear()
    _ORDER.clear()


def tool(name: str, description: str, params: Optional[Dict[str, Dict[str, Any]]] = None):
    param_specs: Dict[str, ParamSpec] = {}
    for pname, pmeta in (params or {}).items():
        param_specs[pname] = ParamSpec(
            type=pmeta.get("type", "str"),
            required=pmeta.get("required", True),
            desc=pmeta.get("desc", ""),
            default=pmeta.get("default", None),
        )

    def decorator(func):
        register(ToolSpec(name=name, description=description, params=param_specs, handler=func))
        return func

    return decorator


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in ("true", "yes", "1", "on"):
        return True
    if text in ("false", "no", "0", "off", ""):
        return False
    raise ValueError(f"not a boolean: {value!r}")


_COERCERS: Dict[str, Callable] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": _to_bool,
}


def coerce_and_validate(spec: ToolSpec, raw_args: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], Optional[str]]:
    if raw_args is None:
        raw_args = {}
    result: Dict[str, Any] = {}
    for pname, pspec in spec.params.items():
        if pname in raw_args and raw_args[pname] is not None:
            coercer = _COERCERS.get(pspec.type, str)
            try:
                result[pname] = coercer(raw_args[pname])
            except (TypeError, ValueError):
                return {}, f"param {pname!r} not coercible to {pspec.type}"
        elif pspec.required:
            return {}, f"missing required param {pname!r}"
        else:
            result[pname] = pspec.default
    return result, None