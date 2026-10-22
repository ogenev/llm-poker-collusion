"""Check six basic actions twice, with fresh prompts and no response repair."""

import argparse
import asyncio
import json
from pathlib import Path

from poker_collusion.poker_basics import BasicsConfig, basics_plan
from poker_collusion.poker_basics_run import prepare_basics, run_basics
from poker_collusion.pricing import configure_model_cost


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, help="New directory for this attempt")
    parser.add_argument("--offline", action="store_true", help="Use a synthetic scripted model")
    parser.add_argument("--preflight", action="store_true", help="Initialize without model calls")
    parser.add_argument("--model-cost-config", type=Path)
    args = parser.parse_args()
    try:
        requested = BasicsConfig.from_json(args.config.read_text())
        if not args.preflight and args.output is None:
            raise ValueError("--output is required for execution")
        if args.model_cost_config:
            configure_model_cost(requested.model.model, args.model_cost_config)
        effective, model = prepare_basics(requested, offline=args.offline)
        if args.preflight:
            print(
                json.dumps(
                    {
                        "client_initialized": True,
                        "api_calls": 0,
                        "mock": args.offline,
                        "plan": basics_plan(effective),
                    },
                    indent=2,
                )
            )
            return
        summary = asyncio.run(
            run_basics(effective, args.output, model=model, requested_config=requested)
        )
    except Exception as error:
        parser.error(str(error))
    print(json.dumps({"output": str(args.output), **summary}, indent=2))
    if summary["result"] != "pass":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
