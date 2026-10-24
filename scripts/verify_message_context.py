"""Verify a saved message-context diagnostic without making model calls."""

import argparse
import asyncio
import json
from pathlib import Path

from poker_collusion.message_context_verification import verify_context


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        report = asyncio.run(verify_context(args.directory))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"passed": False, "error": str(error)}, indent=2))
        raise SystemExit(2) from error
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
