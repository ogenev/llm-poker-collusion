"""Render a standalone interactive HTML report from saved comparison JSON."""

import argparse
import json
from pathlib import Path

from poker_collusion.report_page import write_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("comparison", type=Path, help="Saved comparison analysis JSON")
    parser.add_argument("--output", required=True, type=Path, help="New standalone HTML file")
    parser.add_argument(
        "--review-pages", type=Path, help="Optional JSON map: session ID to local review HTML path"
    )
    args = parser.parse_args()
    try:
        write_report(args.comparison, args.output, review_pages_path=args.review_pages)
    except (OSError, ValueError, RecursionError) as error:
        print(json.dumps({"generated": False, "error": str(error)}, indent=2))
        raise SystemExit(2) from error
    print(json.dumps({"generated": True, "html": str(args.output), "offline": True}, indent=2))


if __name__ == "__main__":
    main()
