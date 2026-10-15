import asyncio
import json
from pathlib import Path

import pytest
from inspect_ai.model import ChatMessage, GenerateConfig, ModelOutput, get_model
from inspect_ai.tool import ToolChoice, ToolInfo

from poker_collusion.experiment import run_experiment
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.model_adapter import ModelConfig
from poker_collusion.model_log import verify_model_links
from poker_collusion.offline_model import scripted_output
from poker_collusion.records import Channel, SessionConfig

pytestmark = pytest.mark.usefixtures("inspect_runtime")


def test_private_exchange_and_audit_labels_do_not_enter_outsider_model_inputs(
    tmp_path: Path,
) -> None:
    def capture(send: bool) -> dict[str, list[tuple[str, str]]]:
        seen: dict[str, list[tuple[str, str]]] = {"A": [], "B": [], "C": []}

        def output(
            messages: list[ChatMessage],
            tools: list[ToolInfo],
            choice: ToolChoice,
            config: GenerateConfig,
        ) -> ModelOutput:
            assert len(messages) == 2 and [m.role for m in messages] == ["system", "user"]
            view = json.loads(messages[-1].text)
            seen[view["player_id"]].append((messages[0].text, messages[1].text))
            result = scripted_output(messages, tools, choice, config)
            if (
                send
                and view["player_id"] == "A"
                and view["hand_index"] == 0
                and view["round_index"] == 0
            ):
                text = '{"type":"message","text":"only-A-and-B-see-this","recipient":"B"}'
                result.completion = text
                result.choices[0].message.content = text
            return result

        config = ExperimentConfig(
            ModelConfig("mockllm/model"),
            session=SessionConfig(hands=3, memory_hands=1),
            channels=(Channel.PRIVATE,),
        )
        model = get_model("mockllm/model", memoize=False, custom_outputs=output)
        logs = asyncio.run(run_experiment(config, tmp_path / str(send), model=model))
        assert logs[0].samples
        sample = logs[0].samples[0]
        audit = verify_model_links(sample.metadata["model_log"], sample.metadata["session_log"])
        assert audit.status == "complete"
        for prompts in seen.values():
            for system, user in prompts:
                for hidden in (
                    sample.metadata["session_id"],
                    sample.metadata["matched_block_id"],
                    "mockllm/model",
                    "Poker session; player inputs",
                ):
                    assert hidden not in system + user
                if json.loads(user)["hand_index"] == 2:
                    assert "only-A-and-B-see-this" not in user
        return seen

    sent, silent = capture(True), capture(False)
    assert sent["C"] == silent["C"]
    for player in ("A", "B"):
        assert any("only-A-and-B-see-this" in user for _, user in sent[player])
        assert all("only-A-and-B-see-this" not in user for _, user in silent[player])
