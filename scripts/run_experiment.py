"""Run a fresh Inspect experiment from an explicit configuration."""

import argparse
import asyncio
import json
from pathlib import Path

from poker_collusion.experiment import experiment_plan, run_experiment
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.inspect_transport import configured_model
from poker_collusion.offline_model import offline_model
from poker_collusion.pricing import configure_model_cost


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, help="New directory for this attempt")
    parser.add_argument("--offline", action="store_true", help="Use the scripted Inspect mock")
    parser.add_argument(
        "--model-cost-config", type=Path, help="JSON prices for the configured model"
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Validate settings and client setup without API calls",
    )
    args = parser.parse_args()
    try:
        config = ExperimentConfig.from_json(args.config.read_text())
        if args.offline and config.model.model != "mockllm/model":
            raise ValueError("--offline requires model=mockllm/model in the configuration")
        if config.model.model.startswith("mockllm/") and not args.offline:
            raise ValueError("Mock configurations require --offline")
        if not args.preflight and args.output is None:
            raise ValueError("--output is required for execution")
        if args.model_cost_config:
            configure_model_cost(config.model.model, args.model_cost_config)
        plan = experiment_plan(config)
        model = (
            offline_model()
            if args.offline
            else configured_model(config.model, config.max_connections)
        )
        if args.preflight:
            print(json.dumps({"client_initialized": True, "api_calls": 0, "plan": plan}, indent=2))
            return
        logs = asyncio.run(run_experiment(config, args.output, model=model))
    except Exception as error:
        # Provider setup errors (including Inspect prerequisite exceptions)
        # should be concise CLI diagnostics, with no fabricated run result.
        parser.error(str(error))
    statuses = [
        sample.metadata.get("session_status", "incomplete")
        for log in logs
        for sample in log.samples or []
    ]
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sessions": statuses,
                "inspect_logs": [log.location for log in logs],
            },
            indent=2,
        )
    )
    if (
        not statuses
        or any(status != "complete" for status in statuses)
        or any(log.status != "success" for log in logs)
    ):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
