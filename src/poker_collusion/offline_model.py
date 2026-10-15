"""A stateless Inspect mock for offline workflow checks, with synthetic usage."""

import json

from inspect_ai.model import ChatMessage, GenerateConfig, Model, ModelOutput, ModelUsage, get_model
from inspect_ai.tool import ToolChoice, ToolInfo


def scripted_output(
    messages: list[ChatMessage],
    tools: list[ToolInfo],
    tool_choice: ToolChoice,
    config: GenerateConfig,
) -> ModelOutput:
    view = json.loads(messages[-1].text)
    if view["phase"] == "communication":
        decision = {"type": "pass"}
    else:
        actions = view["poker"]["legal_actions"]
        decision = {"type": "bet", "action": "check" if "check" in actions else "call"}
    output = ModelOutput.from_content("mockllm/model", json.dumps(decision))
    # Supplying usage prevents the mock from downloading a tokenizer. These
    # numbers test metering only and must never be interpreted as pilot costs.
    output.usage = ModelUsage(input_tokens=100, output_tokens=10, total_tokens=110)
    output.metadata = {"synthetic_usage": True}
    return output


def offline_model() -> Model:
    return get_model("mockllm/model", memoize=False, custom_outputs=scripted_output)
