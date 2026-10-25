"""Approve only the three fixed source sessions; later probes require separate approval."""

import hashlib
import json
from pathlib import Path
from typing import Any

from poker_collusion.experiment import provenance
from poker_collusion.heldout_source_verify import verify_source


async def require_source_approval(
    approval_path: Path,
    manifest_path: Path,
    *,
    config_path: Path,
    policy_path: Path,
    pricing_path: Path,
    block_index: int,
    output: Path,
) -> dict[str, Any]:
    approval = json.loads(approval_path.read_text())
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    if (
        approval.get("approved") is not True
        or not approval.get("user_message")
        or not approval.get("approved_at")
        or approval.get("preparation_manifest_sha256") != hashlib.sha256(raw).hexdigest()
        or approval.get("maximum_calls") != 1188
        or approval.get("sum_cost_thresholds_usd") != 1.05
        or approval.get("sum_token_thresholds") != 9000000
        or approval.get("paid_probe_calls_authorized") != 0
    ):
        raise ValueError("Explicit approval of the frozen three-source budget is required")
    root = Path.cwd().resolve()
    for name, sha in manifest["frozen_files"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError("Frozen source preparation changed")
    if (
        type(block_index) is not int
        or block_index not in range(3)
        or config_path.resolve() != (root / manifest["source_config"]).resolve()
        or policy_path.resolve() != (root / manifest["selection_policy"]).resolve()
        or pricing_path.resolve() != (root / manifest["pricing_file"]).resolve()
        or output.resolve() != (root / manifest["source_outputs"][block_index]).resolve()
        or output.exists()
    ):
        raise ValueError("Approved source config/policy/pricing/fresh output differs")
    gates = []
    for prior in range(block_index):
        directory = root / manifest["source_outputs"][prior]
        checked = await verify_source(directory, policy_path)
        if (
            not checked["passed"]
            or checked["mock"]
            or checked["block_index"] != prior
            or json.loads((directory / "run.jsonl").read_text().splitlines()[0])["provenance"]
            != provenance()
        ):
            raise ValueError("Every prior source must pass with unchanged runtime; no replacement")
        gates.append(
            {
                k: checked[k]
                for k in ("seed", "calls", "known_cost", "total_tokens", "run_manifest_sha256")
            }
        )
    return {
        "approval_sha256": hashlib.sha256(approval_path.read_bytes()).hexdigest(),
        "preparation_manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "previous_source_gates": gates,
        "source_index": block_index,
        "paid_probe_calls_authorized": 0,
        "human_qualification_decision": None,
    }
