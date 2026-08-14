from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.ai_agent import OfflineAIAgent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SATURDAY offline AI agent")
    parser.add_argument("command", nargs="?", default="what can you do")
    parser.add_argument("--storage-dir", default="data", help="Directory used to persist agent memory")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Install dependencies and download models before chatting (see --category)",
    )
    parser.add_argument(
        "--download",
        nargs="?",
        const="all",
        metavar="CATEGORY",
        help="Download AI models (all, agentic, voice-stt, voice-tts, vision) then exit",
    )
    parser.add_argument(
        "--category",
        action="append",
        help="Model/dependency categories to install when --setup is used (repeatable)",
    )
    args = parser.parse_args()

    if args.download is not None:
        from saturday_downloader import download

        return download(categories=[args.download])

    if args.setup:
        from saturday_downloader import setup

        return setup(include_models=False, categories=args.category)

    agent = OfflineAIAgent(storage_dir=Path(args.storage_dir))
    result = agent.process_command(args.command)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["message"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
