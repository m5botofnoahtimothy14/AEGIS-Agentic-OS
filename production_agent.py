from __future__ import annotations

import argparse
from pathlib import Path

from core.agent_service import run_agent_service


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SATURDAY agent as a production service")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--storage-dir", default="data")
    args = parser.parse_args()
    run_agent_service(host=args.host, port=args.port, storage_dir=str(Path(args.storage_dir)))


if __name__ == "__main__":
    main()
