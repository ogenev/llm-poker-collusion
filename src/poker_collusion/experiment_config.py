"""Validated, versioned configuration for matched Phase 1 Inspect sessions."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import cast

from poker_collusion.model_adapter import ModelConfig, _read_object
from poker_collusion.prompts import Instruction
from poker_collusion.records import Channel, SessionConfig, require_int
from poker_collusion.serialization import canonical, config_record, read_config


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    model: ModelConfig
    session: SessionConfig = field(default_factory=SessionConfig)
    seeds: tuple[int, ...] = (0,)
    channels: tuple[Channel, ...] = (Channel.NONE, Channel.PUBLIC, Channel.PRIVATE)
    max_samples: int = 1
    max_connections: int = 3
    token_limit: int = 100_000
    cost_limit: float | None = None
    session_time_limit: float = 600.0

    def __post_init__(self) -> None:
        if not isinstance(self.model, ModelConfig) or not isinstance(self.session, SessionConfig):
            raise ValueError("Expected validated model and session configurations")
        if self.session.channel != Channel.NONE:
            raise ValueError(
                "The session template uses channel=none; choose conditions in channels"
            )
        if not isinstance(self.seeds, tuple) or not self.seeds:
            raise ValueError("seeds must be a nonempty tuple")
        for seed in self.seeds:
            require_int(seed, "seed")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Matched block seeds must be unique")
        if (
            not isinstance(self.channels, tuple)
            or not self.channels
            or any(not isinstance(channel, Channel) for channel in self.channels)
            or len(set(self.channels)) != len(self.channels)
        ):
            raise ValueError("channels must be a nonempty tuple of distinct Phase 1 channels")
        if (
            self.model.instruction == Instruction.COORDINATION_CONTROL
            and Channel.NONE in self.channels
        ):
            raise ValueError("The coordination control requires communication-enabled channels")
        for name in ("max_samples", "max_connections", "token_limit"):
            if require_int(getattr(self, name), name) < 1:
                raise ValueError(f"{name} must be positive")
        for name in ("cost_limit", "session_time_limit"):
            value = getattr(self, name)
            if name == "cost_limit" and value is None:
                continue
            try:
                valid = type(value) in (int, float) and math.isfinite(value) and value > 0
            except OverflowError:
                valid = False
            if not valid:
                raise ValueError(f"{name} must be finite and positive")

    def to_json(self) -> str:
        return canonical(
            {
                "kind": "experiment_config",
                "version": 1,
                "model": _read_object(self.model.to_json()),
                "session": config_record(self.session),
                "seeds": self.seeds,
                "channels": self.channels,
                "max_samples": self.max_samples,
                "max_connections": self.max_connections,
                "token_limit": self.token_limit,
                "cost_limit": self.cost_limit,
                "session_time_limit": self.session_time_limit,
            }
        )

    @classmethod
    def from_json(cls, text: str) -> ExperimentConfig:
        data = _read_object(text)
        if (
            set(data)
            != {
                "kind",
                "version",
                "model",
                "session",
                "seeds",
                "channels",
                "max_samples",
                "max_connections",
                "token_limit",
                "cost_limit",
                "session_time_limit",
            }
            or data["kind"] != "experiment_config"
            or type(data["version"]) is not int
            or data["version"] != 1
        ):
            raise ValueError("Unsupported experiment configuration record")
        seeds, channels = data["seeds"], data["channels"]
        if not isinstance(seeds, list) or not isinstance(channels, list):
            raise ValueError("seeds and channels must be arrays")
        return cls(
            model=ModelConfig.from_json(canonical(data["model"])),
            session=read_config(data["session"]),
            seeds=tuple(seeds),
            channels=tuple(Channel(channel) for channel in channels),
            max_samples=require_int(data["max_samples"], "max_samples"),
            max_connections=require_int(data["max_connections"], "max_connections"),
            token_limit=require_int(data["token_limit"], "token_limit"),
            cost_limit=cast(float | None, data["cost_limit"]),
            session_time_limit=cast(float, data["session_time_limit"]),
        )
