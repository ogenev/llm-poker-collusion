"""Freeze or verify a duration matrix offline; this command never generates model responses."""

import argparse
import asyncio
import json
from pathlib import Path

from poker_collusion.duration_study import duration_plan, verify_duration_study
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.pricing import configure_model_cost


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("short_config", type=Path)
    parser.add_argument("long_config", type=Path)
    parser.add_argument("--model-cost-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New plan or verification JSON")
    parser.add_argument("--verify-root", type=Path, help="Check all six planned saved batches")
    args = parser.parse_args()
    try:
        short = ExperimentConfig.from_json(args.short_config.read_text())
        long = ExperimentConfig.from_json(args.long_config.read_text())
        configure_model_cost(short.model.model, args.model_cost_config)
        plan = duration_plan(short, long)
        result = (
            asyncio.run(verify_duration_study(plan, args.verify_root))
            if args.verify_root is not None
            else plan
        )
        with args.output.open("x") as destination:
            json.dump(result, destination, indent=2)
            destination.write("\n")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps({"output": str(args.output), "paid_calls": 0, "passed": result.get("passed")}))
    if args.verify_root is not None and not result["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
