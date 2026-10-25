"""Prepare or run the fixed Luna honesty probe; live execution requires exact budget approval."""

import argparse
import asyncio
import json
from pathlib import Path

from poker_collusion.honesty_probe import HonestyConfig, honesty_plan
from poker_collusion.honesty_probe_approval import require_approval
from poker_collusion.honesty_probe_run import prepare_honesty, run_honesty
from poker_collusion.pricing import configure_model_cost


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--model-cost-config", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--previous-run", type=Path)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--preparation-manifest", type=Path)
    args = parser.parse_args()
    try:
        requested = HonestyConfig.from_json(args.config.read_text())
        configure_model_cost(requested.model.model, args.model_cost_config)
        authorization = None
        if not args.preflight:
            if args.output is None:
                raise ValueError("A fresh --output is required")
            if not args.offline:
                if args.approval is None or args.preparation_manifest is None:
                    raise ValueError(
                        "Paid execution requires --approval and --preparation-manifest"
                    )
                authorization = require_approval(
                    args.approval,
                    args.preparation_manifest,
                    config_path=args.config,
                    pricing_path=args.model_cost_config,
                    output=args.output,
                    previous_run=args.previous_run,
                )
        effective, model = prepare_honesty(requested, offline=args.offline)
        if args.preflight:
            print(
                json.dumps(
                    {"client_initialized": True, "api_calls": 0, "plan": honesty_plan(effective)},
                    indent=2,
                )
            )
            return
        summary = asyncio.run(
            run_honesty(
                effective,
                args.output,
                model=model,
                requested=requested,
                previous_run=args.previous_run,
                authorization=authorization,
            )
        )
    except Exception as error:
        parser.error(str(error))
    print(json.dumps({k: v for k, v in summary.items() if k != "probes"}, indent=2))
    if summary["result"] != "complete":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
