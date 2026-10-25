"""Bind a live attempt to the exact prepared files, output paths and user budget approval."""

import hashlib
import json
from pathlib import Path
from typing import Any

from poker_collusion.honesty_probe import HonestyConfig


def require_approval(
    approval_path: Path,
    manifest_path: Path,
    *,
    config_path: Path,
    pricing_path: Path,
    output: Path,
    previous_run: Path | None,
) -> dict[str, Any]:
    approval = json.loads(approval_path.read_text())
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    if (
        approval.get("approved") is not True
        or not approval.get("user_message")
        or not approval.get("approved_at")
        or approval.get("preparation_manifest_sha256") != hashlib.sha256(raw).hexdigest()
        or approval.get("maximum_calls") != 120
        or approval.get("sum_cost_thresholds_usd") != 0.5
        or approval.get("sum_token_thresholds") != 1_000_000
    ):
        raise ValueError("Explicit approval of this frozen 120-call budget is required")
    root = Path.cwd().resolve()
    for name, sha in manifest["frozen_files"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError("Frozen preparation changed; prepare and approve a new plan")
    config = HonestyConfig.from_json(config_path.read_text())
    expected_config = root / manifest["stage_configs"][config.stage]
    expected_output = root / manifest["live_outputs"][config.stage]
    if (
        config_path.resolve() != expected_config.resolve()
        or pricing_path.resolve() != (root / manifest["pricing_file"]).resolve()
        or output.resolve() != expected_output.resolve()
        or output.exists()
    ):
        raise ValueError("Approved config/pricing/fresh output differs; no retries or replacement")
    if config.stage == "completion":
        if (
            previous_run is None
            or previous_run.resolve() != (root / manifest["live_outputs"]["screen"]).resolve()
        ):
            raise ValueError("Completion must verify the approved screen attempt")
    elif previous_run is not None:
        raise ValueError("Screen must not consume another run")
    return {
        "approval_sha256": hashlib.sha256(approval_path.read_bytes()).hexdigest(),
        "preparation_manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "paid_scope": "One fixed attempt per approved output; 12 screen plus108 completion calls",
    }
