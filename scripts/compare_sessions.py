"""Compare saved matched Inspect sessions and selected reviews without model calls."""

import argparse
import asyncio
import json
from pathlib import Path

from poker_collusion.comparison import compare_sessions, write_comparison


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="New comparison JSON file")
    args = parser.parse_args()
    try:
        report = asyncio.run(compare_sessions(args.manifest))
        write_comparison(args.output, report)
    except (OSError, ValueError) as error:
        print(json.dumps({"compared": False, "error": str(error)}, indent=2))
        raise SystemExit(2) from error
    print(
        json.dumps(
            {
                "compared": True,
                "output": str(args.output),
                "dataset_role": report["dataset_role"],
                "planned_blocks": report["planned_blocks"],
                "planned_sessions": report["planned_sessions"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
