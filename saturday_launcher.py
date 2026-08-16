#!/usr/bin/env python3
"""SATURDAY AI OS - production launcher.

Works both from source and from a PyInstaller-frozen .exe.
When frozen, the working directory is switched to the folder
containing the executable so relative data paths (logs/, data/,
core/ui/...) resolve correctly.
"""

import os
import sys
from pathlib import Path


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def main() -> int:
    app_dir = _app_dir()
    os.chdir(app_dir)
    sys.path.insert(0, str(app_dir))

    os.environ.setdefault("SATURDAY_MODE", "production")

    (app_dir / "logs").mkdir(exist_ok=True)
    (app_dir / "data").mkdir(exist_ok=True)

    import run_production

    return run_production.main()


if __name__ == "__main__":
    sys.exit(main())
