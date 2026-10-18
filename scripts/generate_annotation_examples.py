"""Generate six offline rubric examples with real journals and scripted annotations."""

import argparse
import asyncio
import json
from pathlib import Path

from poker_collusion.annotation_examples import generate_examples


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="New output directory; must not already exist")
    args = parser.parse_args()
    try:
        examples = asyncio.run(generate_examples(args.directory))
    except (OSError, ValueError) as error:
        print(json.dumps({"generated": False, "error": str(error)}, indent=2))
        raise SystemExit(2) from error
    print(
        json.dumps(
            {
                "generated": True,
                "examples": len(examples),
                "directory": str(args.directory),
                "reviewer_kind": "scripted",
                "replayed_and_validated": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
