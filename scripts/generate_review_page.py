"""Generate a standalone HTML review form for a saved session (no model calls)."""

import argparse
import json
from pathlib import Path

from poker_collusion.review_page import write_review_page


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="Stable saved session journal")
    parser.add_argument("--output", type=Path, required=True, help="New HTML file to create")
    args = parser.parse_args()
    try:
        write_review_page(args.log, args.output)
    except (OSError, ValueError) as error:
        print(json.dumps({"generated": False, "error": str(error)}, indent=2))
        raise SystemExit(2) from error
    print(json.dumps({"generated": True, "html": str(args.output), "offline": True}, indent=2))


if __name__ == "__main__":
    main()
