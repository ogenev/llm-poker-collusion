"""Native source evidence plus prospective selection and explicit provider/usage checks."""

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from inspect_ai.model import ModelCost, ModelInfo, get_model_info, set_model_info

from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.heldout_selection import POLICY_SHA256, verify_selection
from poker_collusion.heldout_source_run import validate_source_config
from poker_collusion.serialization import canonical
from poker_collusion.verification import verify_run


async def verify_source(directory: Path, policy_path: Path) -> dict[str, Any]:
    start = json.loads((directory / "run.jsonl").read_text().splitlines()[0])
    config = ExperimentConfig.from_json(canonical(start["config"]))
    validate_source_config(config)
    if type(start.get("block_index")) is not int:
        raise ValueError("Exactly one original source block is required")
    if start.get("selection_policy_sha256") != POLICY_SHA256:
        raise ValueError("Missing frozen selection policy")
    mock = config.model.model == "mockllm/model"
    if mock:
        set_model_info(
            "mockllm/model",
            ModelInfo(cost=ModelCost(input=0, output=0, input_cache_read=0, input_cache_write=0)),
        )
    elif not start.get("authorization"):
        raise ValueError("Missing source-stage approval record")
    native = await verify_run(directory)
    if not native["passed"]:
        return {
            "passed": False,
            "native": native,
            "selection_certified": False,
            "paid_verification_calls": 0,
            "human_annotations": 0,
        }
    if len(native["sessions"]) != 1:
        raise ValueError("Expected one source session per attempt")
    session = native["sessions"][0]
    seed = config.seeds[start["block_index"]]
    path = directory / "sessions" / session["session_id"]
    selected = verify_selection(path, policy_path, seed)
    rows = [json.loads(s) for s in (path / "model.jsonl").read_text().splitlines()]
    starts = {r["data"]["request_id"]: r["data"] for r in rows if r["event"] == "call_started"}
    info = get_model_info(config.model.model)
    if info is None or info.cost is None:
        raise ValueError("Explicit pricing required for source verification")
    rates = info.cost.model_dump()
    costs = []
    response_ids = []
    for row in rows:
        if row["event"] != "call_finished":
            continue
        result = row["data"]
        output = result["output"]
        usage = output["usage"]
        cost = (
            usage["input_tokens"] * rates["input"]
            + usage["output_tokens"] * rates["output"]
            + (usage["input_tokens_cache_read"] or 0) * rates["input_cache_read"]
            + (usage["input_tokens_cache_write"] or 0) * rates["input_cache_write"]
        ) / 1e6
        if not math.isclose(cost, usage["total_cost"], abs_tol=1e-12):
            raise ValueError("Source usage/pricing differs")
        costs.append(cost)
        if mock:
            continue
        events = result["model_events"]
        if len(events) != 1:
            raise ValueError("Expected exactly one provider event")
        request = events[0]["call"]["request"]
        response = events[0]["call"]["response"]
        prompt = starts[result["request_id"]]["prompt"]
        if (
            request.get("model") != "gpt-6-luna"
            or request.get("reasoning_effort") != "medium"
            or request.get("max_completion_tokens") != 4096
            or request.get("n") != 1
            or request.get("temperature") is not None
            or request.get("tools") not in (None, [])
            or request.get("tool_choice") not in (None, "none")
            or request.get("messages")
            != [
                {"role": "developer", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]},
            ]
            or response.get("model") != output["model"]
            or len(response.get("choices", [])) != 1
            or response["choices"][0]["message"]["content"] != output["completion"]
            or response.get("usage", {}).get("total_tokens") != usage["total_tokens"]
            or response["usage"].get("completion_tokens") != usage["output_tokens"]
            or response["usage"].get("prompt_tokens")
            != usage["total_tokens"] - usage["output_tokens"]
        ):
            raise ValueError("Raw medium/strict provider input/output/usage differs")
        response_ids.append(response["id"])
    cost_total = math.fsum(costs)
    if (
        not 0 < session["calls"] <= 396
        or session["calls"] != len(costs)
        or not 0 < session["total_tokens"] <= config.token_limit
        or cost_total > 0.35
        or not math.isclose(cost_total, session["cost"], abs_tol=1e-12)
        or not mock
        and len(set(response_ids)) != len(response_ids)
    ):
        raise ValueError("Source call/token/cost bound or response identity differs")
    return {
        "passed": True,
        "kind": "heldout_source_verification",
        "version": 1,
        "seed": seed,
        "block_index": start["block_index"],
        "run_id": start["run_id"],
        "mock": mock,
        "native": native,
        "selection": selected,
        "known_cost": cost_total,
        "calls": session["calls"],
        "total_tokens": session["total_tokens"],
        "run_manifest_sha256": hashlib.sha256((directory / "run.jsonl").read_bytes()).hexdigest(),
        "human_annotations": 0,
        "human_primary_estimate": None,
        "paid_verification_calls": 0,
        "scope": "Source execution/provider/replay and prospective selection integrity only",
    }
