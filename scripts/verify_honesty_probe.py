"""Verify an available completed honesty-probe stage without any model generation."""

import argparse
import asyncio
import json
from pathlib import Path

from poker_collusion.honesty_probe import HonestyConfig
from poker_collusion.honesty_probe_verify import verify_honesty
from poker_collusion.pricing import configure_model_cost
from poker_collusion.serialization import canonical


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--model-cost-config", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        start = json.loads((args.directory / "run.jsonl").read_text().splitlines()[0])
        requested = HonestyConfig.from_json(canonical(start["requested_config"]))
        configure_model_cost(requested.model.model, args.model_cost_config)
        checked = asyncio.run(verify_honesty(args.directory))
        if args.output:
            with args.output.open("x") as f:
                json.dump(checked, f, indent=2)
                f.write("\n")
    except Exception as error:
        parser.error(str(error))
    print(json.dumps(checked, indent=2))
    if not checked["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
