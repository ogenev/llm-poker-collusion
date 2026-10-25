"""Seal prospectively selected inputs without copying their natural recipient replies."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from poker_collusion.durable_jsonl import DurableJsonl
from poker_collusion.experiment import provenance
from poker_collusion.heldout_selection import load_policy
from poker_collusion.heldout_source_verify import verify_source
from poker_collusion.history_context import source_view
from poker_collusion.prompts import render_prompt
from poker_collusion.records import Message
from poker_collusion.serialization import canonical, digest


def context_variants(context: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    original = source_view(context["view"])
    focal = Message(**context["focal_message"])
    if original.messages.count(focal) != 1:
        raise ValueError("Expected the exact single focal incoming message")
    proposed = policy["future_probe_not_yet_authorized"]
    variants = []
    for condition in proposed["conditions"]:
        if condition == "focal_message_withheld":
            messages = tuple(m for m in original.messages if m != focal)
        else:
            key = "truth_request" if condition == "standard_truth_request" else "neutral_request"
            messages = tuple(
                replace(m, text=proposed[key]) if m == focal else m for m in original.messages
            )
        view = replace(original, messages=messages)
        prompt = render_prompt(view, response_format="strict_json_schema")
        variants.append(
            {
                "condition": condition,
                "view": json.loads(canonical(view)),
                "prompt": json.loads(canonical(prompt)),
                "prompt_sha256": prompt.sha256,
            }
        )
    return variants


async def seal_cohort(directories: list[Path], policy_path: Path, output: Path) -> dict[str, Any]:
    policy = load_policy(policy_path)
    if len(directories) != 3 or len({p.resolve() for p in directories}) != 3:
        raise ValueError("Exactly three distinct planned source attempts required")
    verified = []
    for block, path in enumerate(directories):
        result = await verify_source(path, policy_path)
        if (
            not result["passed"]
            or result["seed"] != policy["seeds"][block]
            or result["block_index"] != block
        ):
            raise ValueError("Complete source attempts in original seed order required")
        start = json.loads((path / "run.jsonl").read_text().splitlines()[0])
        if start["provenance"] != provenance():
            raise ValueError("Seal with the exact source collection runtime")
        verified.append(result)
    if len({r["mock"] for r in verified}) != 1:
        raise ValueError("Do not mix synthetic and paid evidence")
    contexts = []
    for checked in verified:
        for context in checked["selection"]["contexts"]:
            contexts.append(
                {
                    **context,
                    "source_run_manifest_sha256": checked["run_manifest_sha256"],
                    "source_session_sha256": checked["selection"]["source_session_sha256"],
                    "source_model_sha256": checked["selection"]["source_model_sha256"],
                    "variants": context_variants(context, policy),
                }
            )
    if len({c["context_id"] for c in contexts}) != len(contexts):
        raise ValueError("Duplicate selected context")
    summary = {
        "kind": "heldout_source_cohort",
        "version": 1,
        "mock": verified[0]["mock"],
        "planned_source_sessions": 3,
        "completed_source_sessions": 3,
        "source_sessions_represented": sum(
            bool(r["selection"]["selected_contexts"]) for r in verified
        ),
        "selected_contexts": len(contexts),
        "maximum_planned_contexts": 6,
        "underfilled": len(contexts) < 6,
        "contexts_sha256": digest(contexts),
        "natural_current_replies_included": False,
        "human_annotations": 0,
        "human_primary_estimate": None,
        "coalition_inference": None,
        "paid_calls": 0,
        "future_probe_calls_at_ten_per_condition": len(contexts) * 30,
        "future_probe_calls_authorized": 0,
        "rule_change_or_backfill": False,
        "scope": (
            "Prospective input cohort only; future probing needs an exact manifest "
            "and separate approval"
        ),
    }
    output.mkdir(parents=True, exist_ok=False)
    with DurableJsonl(output / "contexts.jsonl") as f:
        for context in contexts:
            f.write(context)
    with DurableJsonl(output / "source-verification.jsonl") as f:
        for result in verified:
            f.write(result)
    with DurableJsonl(output / "summary.json") as f:
        f.write(summary)
    return summary
