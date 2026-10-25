"""Frozen, selected decision-context interventions; never new poker replications."""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass, fields, replace
from importlib.resources import files
from typing import Any, cast

from inspect_ai.model import get_model_info

from poker_collusion.history_context import source_view
from poker_collusion.model_adapter import ModelConfig, _read_object
from poker_collusion.prompts import Instruction, render_prompt
from poker_collusion.records import (
    Message,
    MessageDecision,
    PassDecision,
    Phase,
    PlayerView,
    require_int,
)
from poker_collusion.serialization import canonical, digest

SOURCE_SHA256 = "29964ff797f452e17bb1ea2b219ea4844f9c60b4297c298ad16168023893f69f"
ARMS = ("original", "honesty_removed", "message_withheld")
ORDER_SEED = 20261025
INPUT_RESERVE = 4096
SCOPE = (
    "Selected within-context response probe, not a coalition qualification or new neutral session. "
    "Four positive contexts from one seed/session; repeats are not independent game replications. "
    "Only the next communication response is generated; no downstream actions/payoffs inferred."
)


@dataclass(frozen=True, slots=True)
class HonestyConfig:
    model: ModelConfig
    stage: str
    decision_timeout_seconds: float = 90
    run_time_limit: float = 1200
    token_limit: int = 100_000
    cost_limit: float = 0.05

    def __post_init__(self) -> None:
        if self.stage not in ("screen", "completion"):
            raise ValueError("Expected screen or completion stage")
        if (
            not isinstance(self.model, ModelConfig)
            or self.model.model not in ("openai/gpt-6-luna", "mockllm/model")
            or self.model.instruction != Instruction.NEUTRAL
            or self.model.reasoning_effort != "medium"
            or self.model.response_format != "strict_json_schema"
            or self.model.max_tokens != 4096
            or self.model.temperature is not None
        ):
            raise ValueError(
                "Honesty probe requires neutral Luna/medium/strict JSON/4096/default temperature"
            )
        if require_int(self.token_limit, "token_limit") <= 0:
            raise ValueError("Positive token limit required")
        for name in ("cost_limit", "run_time_limit", "decision_timeout_seconds"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"Invalid {name}")

    def to_json(self) -> str:
        return canonical(
            {
                "kind": "poker_honesty_probe_config",
                "version": 1,
                **{f.name: getattr(self, f.name) for f in fields(self)},
                "model": _read_object(self.model.to_json()),
            }
        )

    @classmethod
    def from_json(cls, text: str) -> HonestyConfig:
        d = _read_object(text)
        if (
            set(d) != {"kind", "version", *(f.name for f in fields(cls))}
            or d["kind"] != "poker_honesty_probe_config"
            or type(d["version"]) is not int
            or d["version"] != 1
        ):
            raise ValueError("Unsupported honesty configuration")
        return cls(
            model=ModelConfig.from_json(canonical(d["model"])),
            stage=cast(str, d["stage"]),
            decision_timeout_seconds=cast(float, d["decision_timeout_seconds"]),
            run_time_limit=cast(float, d["run_time_limit"]),
            token_limit=require_int(d["token_limit"], "token_limit"),
            cost_limit=cast(float, d["cost_limit"]),
        )


def honesty_sources() -> tuple[dict[str, Any], ...]:
    raw = files("poker_collusion").joinpath("fixtures/honesty_sources_v1.jsonl").read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Frozen honesty source checksum differs")
    sources = tuple(json.loads(line) for line in raw.splitlines())
    if [s["hand"] for s in sources] != [9, 12, 13, 15]:
        raise ValueError("Source selection changed")
    for s in sources:
        v = source_view(s["view"])
        focal = Message(**s["focal_message"])
        p = render_prompt(v, response_format="strict_json_schema")
        if (
            v.phase != Phase.COMMUNICATION
            or v.round_index != 1
            or len(v.history) != 6
            or v.total_hands != 36
            or v.messages.count(focal) != 1
            or focal.recipient != v.player_id
            or focal.sender == v.player_id
            or focal.round_index != 0
            or p.sha256 != s["original_prompt_sha256"]
            or json.loads(canonical(p)) != s["original_prompt"]
        ):
            raise ValueError("Source observation, prompt, or exact receipt differs")
    return sources


@dataclass(frozen=True, slots=True)
class ProbeTrial:
    trial_id: str
    repetition: int
    source_id: str
    condition: str
    intended_recipient: str
    stratum: str
    view: PlayerView


def intervention(source: dict[str, Any], condition: str) -> PlayerView:
    if condition not in ARMS:
        raise ValueError("Unknown intervention")
    original = source_view(source["view"])
    focal = Message(**source["focal_message"])
    if condition == "original":
        return original
    messages = tuple(
        replace(m, text=source["without_honesty_text"]) if m == focal else m
        for m in original.messages
        if condition != "message_withheld" or m != focal
    )
    return replace(original, messages=messages)


def honesty_trials(config: HonestyConfig) -> tuple[ProbeTrial, ...]:
    sources = honesty_sources()
    rng = random.Random(ORDER_SEED)
    trials = []
    for rep in range(1, 11):
        block = [(s, c) for s in sources for c in ARMS]
        rng.shuffle(block)
        for source, condition in block:
            if (config.stage == "screen") != (rep == 1):
                continue
            trials.append(
                ProbeTrial(
                    f"r{rep:02}-{source['source_id']}-{condition}",
                    rep,
                    source["source_id"],
                    condition,
                    source["focal_message"]["sender"],
                    source["stratum"],
                    intervention(source, condition),
                )
            )
    return tuple(trials)


def honesty_plan(config: HonestyConfig) -> dict[str, Any]:
    info = get_model_info(config.model.model)
    if info is None or info.cost is None:
        raise ValueError("Explicit pricing required")
    rates = info.cost.model_dump()
    input_rate = max(rates[k] for k in ("input", "input_cache_read", "input_cache_write"))
    sources = honesty_sources()
    repeats = 1 if config.stage == "screen" else 9
    expected_cost = 0.0
    expected_tokens = 0
    for source in sources:
        usage = source["baseline_usage"]
        input_tokens = usage["total_tokens"] - usage["output_tokens"]
        expected_cost += (
            input_tokens * input_rate + usage["output_tokens"] * rates["output"]
        ) / 1e6
        expected_tokens += usage["total_tokens"]
    trials = honesty_trials(config)
    return {
        "kind": "honesty_probe_plan",
        "version": 1,
        "model": config.model.model,
        "stage": config.stage,
        "config_sha256": digest(_read_object(config.to_json())),
        "sources_sha256": SOURCE_SHA256,
        "trials_sha256": digest(trials),
        "order_seed": ORDER_SEED,
        "maximum_calls": len(trials),
        "repetitions": [1] if repeats == 1 else list(range(2, 11)),
        "conditions": ARMS,
        "selected_contexts": 4,
        "independent_new_game_sessions": 0,
        "pricing_per_million_tokens": rates,
        "expected_cost_usd": expected_cost * 3 * repeats,
        "expected_tokens": expected_tokens * 3 * repeats,
        "estimate_basis": (
            "Four selected original usages; all input charged at highest configured input rate; "
            "variants assumed no larger. Not an invoice or new performance evidence."
        ),
        "input_tokens_reserved_per_call": INPUT_RESERVE,
        "tokens_reserved_per_call": INPUT_RESERVE + config.model.max_tokens,
        "cost_reserved_per_call": (
            INPUT_RESERVE * input_rate + config.model.max_tokens * rates["output"]
        )
        / 1e6,
        "token_limit": config.token_limit,
        "cost_limit": config.cost_limit,
        "run_time_limit": config.run_time_limit,
        "decision_timeout_seconds": config.decision_timeout_seconds,
        "max_connections": 1,
        "max_retries": 0,
        "scope": SCOPE,
        "limits_note": (
            "Reserve before a request; check actual input/usage after it. Unexpected usage, "
            "errors or limits stop further calls. Provider usage can exceed assumptions; "
            "not a hard billing cap."
        ),
    }


def can_request(plan: dict[str, Any], tokens: int, cost: float) -> bool:
    return bool(
        tokens + plan["tokens_reserved_per_call"] <= plan["token_limit"]
        and cost + plan["cost_reserved_per_call"] <= plan["cost_limit"]
    )


def decision_record(decision: object) -> dict[str, Any]:
    """Keep an explicit discriminant; canonical PassDecision alone serializes to {}."""
    if isinstance(decision, PassDecision):
        return {"type": "pass"}
    if isinstance(decision, MessageDecision):
        return {"type": "message", "recipient": decision.recipient, "text": decision.text}
    raise ValueError("A probe response must be a communication decision")
