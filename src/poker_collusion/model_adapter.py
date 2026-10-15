"""Provider-independent requests and strict, single-response parsing.

The caller supplies the async text generator; Inspect transport adds durable
provider evidence while the session engine owns legality and memory.
"""

from __future__ import annotations

import json
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from poker_collusion.prompts import Instruction, Prompt, render_prompt
from poker_collusion.records import (
    Action,
    BetDecision,
    Decision,
    DecisionParseError,
    MessageDecision,
    PassDecision,
    PlayerView,
    require_int,
)
from poker_collusion.serialization import canonical, digest
from poker_collusion.session_audit import Decider


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value: str) -> object:
    raise ValueError(f"Non-finite JSON number: {value}")


def _read_object(text: str) -> dict[str, object]:
    try:
        data: object = json.loads(
            text, object_pairs_hook=_unique_object, parse_constant=_invalid_constant
        )
    except RecursionError as error:
        raise ValueError("JSON nesting is too deep") from error
    if not isinstance(data, dict):
        raise ValueError("Expected one JSON object")
    return data


@dataclass(frozen=True, slots=True)
class ModelConfig:
    model: str
    instruction: Instruction = Instruction.NEUTRAL
    max_tokens: int = 512
    temperature: float | None = None
    cache: bool = False
    max_retries: int = 0

    def __post_init__(self) -> None:
        if type(self.model) is not str or not self.model or any(c.isspace() for c in self.model):
            raise ValueError("Model must be a nonempty identifier without whitespace")
        if not isinstance(self.instruction, Instruction):
            raise ValueError("Instruction must be an Instruction enum value")
        if require_int(self.max_tokens, "max_tokens") <= 0:
            raise ValueError("max_tokens must be positive")
        if self.temperature is not None:
            try:
                valid_temperature = (
                    type(self.temperature) in (int, float)
                    and math.isfinite(self.temperature)
                    and self.temperature >= 0
                )
            except OverflowError:
                valid_temperature = False
            if not valid_temperature:
                raise ValueError("temperature must be omitted or finite and nonnegative")
        if self.cache is not False:
            raise ValueError("Response caching must be disabled")
        if require_int(self.max_retries, "max_retries") != 0:
            raise ValueError("This increment permits zero retries only")

    def to_json(self) -> str:
        return canonical({"kind": "model_config", "version": 1, "settings": self})

    @classmethod
    def from_json(cls, text: str) -> ModelConfig:
        data = _read_object(text)
        if (
            set(data) != {"kind", "version", "settings"}
            or data["kind"] != "model_config"
            or type(data["version"]) is not int
            or data["version"] != 1
        ):
            raise ValueError("Unsupported model configuration record")
        settings = data["settings"]
        if not isinstance(settings, dict) or set(settings) != {
            "model",
            "instruction",
            "max_tokens",
            "temperature",
            "cache",
            "max_retries",
        }:
            raise ValueError("Invalid model configuration fields")
        return cls(**{**settings, "instruction": Instruction(settings["instruction"])})

    @property
    def sha256(self) -> str:
        return digest(_read_object(self.to_json()))


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """Trusted generator input; only prompt.system/user become model messages."""

    config: ModelConfig
    prompt: Prompt


type GenerateText = Callable[[ModelRequest], Awaitable[str]]


def parse_response(response: str) -> Decision:
    """Decode the exact response shape; the session validates phase and legality.

    Never extract JSON from prose, repair an answer, or substitute an action.
    Malformed text is carried to the session as a replayable invalid candidate.
    """
    if type(response) is not str:
        raise TypeError("The text generator must return a built-in string")
    try:
        data = _read_object(response)
        if data.get("type") == "pass" and set(data) == {"type"}:
            return PassDecision()
        if data.get("type") == "bet" and set(data) == {"type", "action"}:
            if type(data["action"]) is not str:
                raise ValueError("action must be a string")
            return BetDecision(Action(data["action"]))
        if data.get("type") == "message" and set(data) == {"type", "text", "recipient"}:
            if type(data["text"]) is not str or (
                data["recipient"] is not None and type(data["recipient"]) is not str
            ):
                raise ValueError("text must be a string; recipient must be a string or null")
            return MessageDecision(data["text"], data["recipient"])
        raise ValueError("Unknown decision type or fields")
    except ValueError as error:
        raise DecisionParseError(response, str(error)) from error


def model_decider(config: ModelConfig, generate: GenerateText) -> Decider:
    """Build fresh prompts and make exactly one generator call per decision.

    No conversation history or outputs are retained here. The injected generator
    must honor the settings and must not add hidden conversation state/retries.
    The session runner owns timeouts, cancellation, and decision validation.
    """

    async def decide(view: PlayerView) -> Decision:
        request = ModelRequest(config, render_prompt(view, config.instruction))
        return parse_response(await generate(request))

    return decide
