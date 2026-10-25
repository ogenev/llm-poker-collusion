"""Prepare or execute one prospectively sampled source session, with no paid probes."""

import argparse
import asyncio
import json
from dataclasses import replace
from pathlib import Path

from inspect_ai.model import ModelCost, ModelInfo, set_model_info

from poker_collusion.experiment import experiment_plan
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.heldout_selection import POLICY_SHA256, load_policy
from poker_collusion.heldout_source_approval import require_source_approval
from poker_collusion.heldout_source_run import run_heldout_source, validate_source_config
from poker_collusion.inspect_transport import configured_model
from poker_collusion.offline_model import offline_model
from poker_collusion.pricing import configure_model_cost


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("config", type=Path)
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--model-cost-config", type=Path, required=True)
    p.add_argument("--block-index", type=int, required=True, choices=range(3))
    p.add_argument("--output", type=Path)
    p.add_argument("--preflight", action="store_true")
    p.add_argument("--offline", action="store_true")
    p.add_argument("--approval", type=Path)
    p.add_argument("--preparation-manifest", type=Path)
    a = p.parse_args()
    try:
        c = ExperimentConfig.from_json(a.config.read_text())
        validate_source_config(c)
        load_policy(a.policy)
        configure_model_cost(c.model.model, a.model_cost_config)
        authorization = None
        if not a.preflight:
            if a.output is None:
                raise ValueError("Fresh output required")
            if not a.offline:
                if a.approval is None or a.preparation_manifest is None:
                    raise ValueError("Paid source collection requires an explicit approval receipt")
                authorization = asyncio.run(
                    require_source_approval(
                        a.approval,
                        a.preparation_manifest,
                        config_path=a.config,
                        policy_path=a.policy,
                        pricing_path=a.model_cost_config,
                        block_index=a.block_index,
                        output=a.output,
                    )
                )
        if a.offline:
            c = replace(c, model=replace(c.model, model="mockllm/model"))
            set_model_info(
                "mockllm/model",
                ModelInfo(
                    cost=ModelCost(input=0, output=0, input_cache_read=0, input_cache_write=0)
                ),
            )
            model = offline_model()
        else:
            if c.model.model != "openai/gpt-6-luna":
                raise ValueError("Live source requires Luna")
            model = configured_model(c.model, 1)
        if a.preflight:
            print(
                json.dumps(
                    {
                        "api_calls": 0,
                        "client_initialized": True,
                        "plan": experiment_plan(c, block_index=a.block_index),
                        "policy_sha256": POLICY_SHA256,
                        "paid_probe_calls_authorized": 0,
                    },
                    indent=2,
                )
            )
            return
        logs = asyncio.run(
            run_heldout_source(
                c,
                a.output,
                model=model,
                block_index=a.block_index,
                policy_path=a.policy,
                authorization=authorization,
            )
        )
        complete = bool(logs) and all(
            log.status == "success"
            and all(s.metadata.get("session_status") == "complete" for s in log.samples or [])
            for log in logs
        )
        print(json.dumps({"complete": complete, "output": str(a.output), "paid_probe_calls": 0}))
        if not complete:
            raise SystemExit(2)
    except Exception as error:
        p.error(str(error))


if __name__ == "__main__":
    main()
