"""Verify frozen history fixtures, strict provider settings, usage and responses offline."""

import argparse
import asyncio
import json
from pathlib import Path

from poker_collusion.history_context import HistoryContextConfig
from poker_collusion.message_context_verification import verify_context


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        result = asyncio.run(verify_context(args.directory, config_type=HistoryContextConfig))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"passed": False, "error": str(error)}, indent=2))
        raise SystemExit(2) from error
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
