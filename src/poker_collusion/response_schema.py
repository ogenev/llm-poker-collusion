"""Opt-in wire format for strict structured decisions; game legality stays separate."""

from typing import Literal

type ResponseFormat = Literal["text", "strict_json_schema"]

SCHEMA_NAME = "poker_decision_v1"


def validate_response_format(value: ResponseFormat) -> None:
    if type(value) is not str or value not in ("text", "strict_json_schema"):
        raise ValueError("Unsupported response format")


def decision_example(example: str, response_format: ResponseFormat) -> str:
    """Wrap an already-authored response example without changing legacy bytes."""
    return '{"decision":' + example + "}" if response_format == "strict_json_schema" else example


def decision_schema() -> dict[str, object]:
    """A fresh schema with a root object and a nested union of exact decisions.

    It enforces formatting, not which decision is legal in a player's view.
    All required fields include explicit public-message recipient=null. No
    observation, strategy, partner assignment, or example message is added.
    """

    def object_schema(properties: dict[str, object]) -> dict[str, object]:
        return {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        }

    return object_schema(
        {
            "decision": {
                "anyOf": [
                    object_schema({"type": {"type": "string", "enum": ["pass"]}}),
                    object_schema(
                        {
                            "type": {"type": "string", "enum": ["bet"]},
                            "action": {"type": "string", "enum": ["check", "bet", "call", "fold"]},
                        }
                    ),
                    object_schema(
                        {
                            "type": {"type": "string", "enum": ["message"]},
                            "text": {"type": "string"},
                            "recipient": {"type": ["string", "null"]},
                        }
                    ),
                ]
            }
        }
    )
