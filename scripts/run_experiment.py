"""Run a fresh Inspect experiment from an explicit configuration."""

import argparse
import asyncio
import json
from pathlib import Path

from poker_collusion.experiment import run_experiment
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.offline_model import offline_model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", required=True, type=Path, help="New directory for this attempt")
    parser.add_argument("--offline", action="store_true", help="Use the scripted Inspect mock")
    args = parser.parse_args()
    try:
        config = ExperimentConfig.from_json(args.config.read_text())
        if args.offline and config.model.model != "mockllm/model":
            raise ValueError("--offline requires model=mockllm/model in the configuration")
        logs = asyncio.run(
            run_experiment(config, args.output, model=offline_model() if args.offline else None)
        )
    except (OSError, ValueError) as error:
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
