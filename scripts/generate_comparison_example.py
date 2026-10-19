"""Generate a matched preparation example using Inspect's offline scripted model."""

import argparse
import asyncio
import json
from pathlib import Path

from poker_collusion.comparison_example import generate_comparison_example


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output", type=Path, help="New directory for scripted preparation artifacts"
    )
    args = parser.parse_args()
    manifest = asyncio.run(generate_comparison_example(args.output))
    print(json.dumps({"manifest": str(manifest), "dataset_role": "preparation"}, indent=2))


if __name__ == "__main__":
    main()
