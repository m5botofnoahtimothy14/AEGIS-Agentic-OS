from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import List, Optional

import structlog

logger = structlog.get_logger("SATURDAY.Assistant.Loader")


def import_plugin_file(path: Path) -> None:
    try:
        spec = importlib.util.spec_from_file_location(path.stem, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        logger.exception(f"Skipping bad plugin {path}: {e}")


def load_builtins() -> None:
    sys.modules.pop("core.assistant.builtins", None)
    import core.assistant.builtins  # noqa: F401  (decorators register on import)


def load_plugins(dirs: List[Path]) -> None:
    seen = set()
    for directory in dirs:
        resolved = directory.resolve()
        if resolved in seen or not directory.exists():
            continue
        seen.add(resolved)
        for path in sorted(directory.glob("*.py")):
            if path.name.startswith("_") or path.name.endswith(".pyc"):
                continue
            import_plugin_file(path)


def init_tools(root_dir: Optional[Path] = None, user_dir: Optional[Path] = None) -> None:
    load_builtins()
    plugin_dirs = []
    if root_dir is not None:
        plugin_dirs.append(Path(root_dir) / "plugins")
    if user_dir is not None:
        plugin_dirs.append(Path(user_dir) / "plugins")
    load_plugins(plugin_dirs)