import asyncio
import json
import shutil
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from inspect_ai.event import ModelEvent
from inspect_ai.log import read_eval_log, write_eval_log
from inspect_ai.model import ChatMessage, GenerateConfig, ModelOutput, get_model
from inspect_ai.tool import ToolChoice, ToolInfo
from test_comparison import compare, primary, review_path, save, selected_game
from test_comparison import manifest as manifest

import poker_collusion.comparison_inputs as input_module
from poker_collusion.analysis import analyze_session
from poker_collusion.comparison_inputs import InputSnapshot
from poker_collusion.experiment import run_experiment
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.model_adapter import ModelConfig
from poker_collusion.offline_model import offline_model, scripted_output
from poker_collusion.prompts import Instruction
from poker_collusion.records import Channel, SessionConfig
from poker_collusion.serialization import canonical

pytestmark = pytest.mark.usefixtures("inspect_runtime")


def append_run(path: Path, config: ExperimentConfig) -> None:
    asyncio.run(run_experiment(config, path.parent / "second", model=offline_model()))
    data = json.loads(path.read_text())
    data["runs"].append({"directory": "second", "reviews": []})
    save(path, data)


def test_multiple_runs_with_disjoint_seeds_keep_all_expected_sessions(manifest: Path) -> None:
    append_run(
        manifest, ExperimentConfig(ModelConfig("mockllm/model"), SessionConfig(hands=3), seeds=(3,))
    )
    report = compare(manifest)
    assert report["planned_blocks"] == 4 and report["planned_sessions"] == 12
    assert primary(report)["eligible_blocks"] == 3
    assert primary(report, "payoff_AB")["eligible_blocks"] == 4


@pytest.mark.parametrize("case", ["same_seed", "hands", "temperature", "control", "limit"])
def test_incompatible_or_nonindependent_runs_are_rejected(manifest: Path, case: str) -> None:
    config = ExperimentConfig(ModelConfig("mockllm/model"), SessionConfig(hands=3), seeds=(3,))
    if case == "same_seed":
        config = replace(config, seeds=(0,))
    elif case == "hands":
        config = replace(config, session=SessionConfig(hands=1))
    elif case == "temperature":
        config = replace(config, model=replace(config.model, temperature=0.5))
    elif case == "control":
        config = replace(
            config,
            model=replace(config.model, instruction=Instruction.COORDINATION_CONTROL),
            channels=(Channel.PUBLIC, Channel.PRIVATE),
        )
    else:
        config = replace(config, token_limit=5000)
    append_run(manifest, config)
    with pytest.raises(ValueError, match="Repeated seeds|Incompatible"):
        compare(manifest)


def test_copied_run_cannot_double_the_sample_size(manifest: Path) -> None:
    shutil.copytree(manifest.parent / "run", manifest.parent / "copy")
    data = json.loads(manifest.read_text())
    data["runs"].append({"directory": "copy", "reviews": []})
    save(manifest, data)
    with pytest.raises(ValueError, match="Duplicate run identity"):
        compare(manifest)


@pytest.mark.parametrize(
    "case",
    [
        "schedule",
        "rotation",
        "block",
        "channel",
        "epoch",
        "duplicate_sample",
        "raw_input",
        "audit_model",
        "audit_provenance",
        "payoff",
        "wrong_review",
    ],
)
def test_corrupt_inputs_fail_instead_of_becoming_exclusions(manifest: Path, case: str) -> None:
    game = selected_game(manifest)
    if case in ("audit_model", "audit_provenance", "payoff"):
        path = game if case == "payoff" else game.with_name("model.jsonl")
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        if case == "payoff":
            next(r for r in rows if r["event"] == "rewards_settled")["data"]["returns"][0] += 1
        else:
            rows[0]["data"]["model_config_sha256" if case == "audit_model" else "provenance"] = (
                "wrong"
            )
        path.write_text("".join(canonical(row) + "\n" for row in rows))
    elif case == "wrong_review":
        review_path(manifest).write_bytes(review_path(manifest, "block-1-private").read_bytes())
    else:
        path = next((manifest.parent / "run" / "inspect").glob("*.eval"))
        log = read_eval_log(str(path), resolve_attachments="full")
        assert log.samples
        sample = next(s for s in log.samples if s.id == "block-0-private")
        if case in ("schedule", "rotation"):
            saved = json.loads(sample.metadata["schedule"])
            if case == "rotation":
                saved["initial_rotation"] = 1
            else:
                saved["deals"] = [[3 - card for card in deal] for deal in saved["deals"]]
            sample.metadata["schedule"] = canonical(saved)
        elif case == "raw_input":
            next(e for e in sample.events if isinstance(e, ModelEvent)).input[
                -1
            ].content = "changed prompt"
        elif case == "duplicate_sample":
            duplicate = sample.model_copy(deep=True)
            # Inspect's writer replaces a repeated (ID, epoch); use another epoch
            # to retain two copies of the same planned sample in the saved file.
            duplicate.epoch = 2
            log.samples.append(duplicate)
        elif case == "epoch":
            sample.epoch = 2
        else:
            sample.metadata["matched_block_id" if case == "block" else "channel"] = "wrong"
        write_eval_log(log, str(path))
    with pytest.raises(ValueError):
        compare(manifest)


@pytest.mark.parametrize(
    "field", ["journal", "review", "manifest", "model", "index", "inventory", "missing"]
)
def test_changes_during_analysis_are_rejected(
    manifest: Path, field: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = analyze_session
    game = selected_game(manifest)
    index = next((manifest.parent / "run" / "inspect").glob("*.eval"))
    if field == "missing":
        review_path(manifest).rename(review_path(manifest).with_suffix(".saved"))
    changed = False

    async def changing(*args: Any, **kwargs: Any) -> Any:
        nonlocal changed
        result = await original(*args, **kwargs)
        if result.source.session_id == game.parent.name and not changed:
            changed = True
            if field == "inventory":
                (manifest.parent / "run" / "sessions" / "new-attempt").mkdir()
            elif field == "missing":
                review_path(manifest).write_text("now present")
            else:
                path = {
                    "journal": game,
                    "review": review_path(manifest),
                    "manifest": manifest,
                    "model": game.with_name("model.jsonl"),
                    "index": index,
                }[field]
                path.write_bytes(path.read_bytes() + b"\n")
        return result

    monkeypatch.setattr(input_module, "analyze_session", changing)
    with pytest.raises(ValueError):
        compare(manifest)


def test_snapshot_detects_retargeted_symlink(tmp_path: Path) -> None:
    original, replacement, link = (tmp_path / name for name in ("original", "replacement", "link"))
    original.write_text("one")
    replacement.write_text("two")
    link.symlink_to(original)
    snapshot = InputSnapshot(tmp_path)
    snapshot.track(link)
    link.rename(tmp_path / "old-link")
    link.symlink_to(replacement)
    with pytest.raises(ValueError, match="changed"):
        snapshot.finish()


@pytest.mark.parametrize("role", ["pilot", "evaluation"])
def test_preparation_cannot_be_implicitly_promoted_to_research(manifest: Path, role: str) -> None:
    data = json.loads(manifest.read_text())
    data["dataset_role"] = role
    save(manifest, data)
    with pytest.raises(ValueError, match="require human"):
        compare(manifest)
    data["reviewer_kind"] = "human"
    save(manifest, data)
    with pytest.raises(ValueError, match="Mock gameplay"):
        compare(manifest)


@pytest.mark.parametrize(
    "case",
    [
        "duplicate_review",
        "unknown_sample",
        "duplicate_run",
        "unknown_field",
        "duplicate_key",
        "nonfinite",
    ],
)
def test_ambiguous_or_invalid_manifest_selection_is_rejected(manifest: Path, case: str) -> None:
    data = json.loads(manifest.read_text())
    if case == "duplicate_review":
        data["runs"][0]["reviews"].append(data["runs"][0]["reviews"][0])
    elif case == "unknown_sample":
        data["runs"][0]["reviews"][0]["sample_id"] = "unplanned"
    elif case == "duplicate_run":
        data["runs"].append(data["runs"][0])
    elif case == "unknown_field":
        data["channel"] = "private"
    elif case == "nonfinite":
        data["bootstrap"]["confidence"] = float("nan")
    save(manifest, data)
    if case == "duplicate_key":
        manifest.write_text(
            manifest.read_text().replace('"version": 1', '"version": 1, "version": 1')
        )
    with pytest.raises(ValueError):
        compare(manifest)


def test_real_failed_inspect_sessions_are_retained_without_payoff_estimates(tmp_path: Path) -> None:
    def broken(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        output = scripted_output(messages, tools, choice, config)
        output.completion = "invalid JSON"
        output.choices[0].message.content = output.completion
        return output

    config = ExperimentConfig(
        ModelConfig("mockllm/model"),
        SessionConfig(hands=1),
        channels=(Channel.PUBLIC, Channel.PRIVATE),
    )
    model = get_model("mockllm/model", custom_outputs=broken, memoize=False)
    asyncio.run(run_experiment(config, tmp_path / "run", model=model))
    manifest = tmp_path / "comparison.json"
    save(
        manifest,
        {
            "kind": "session_comparison",
            "version": 1,
            "dataset_role": "preparation",
            "reviewer_kind": "human",
            "bootstrap": {"replicates": 100, "seed": 0, "confidence": 0.95},
            "runs": [{"directory": "run", "reviews": []}],
        },
    )
    report = compare(manifest)
    assert report["planned_sessions"] == 2
    assert all(s["analysis"]["source"]["status"] == "failed" for s in report["sessions"])
    assert primary(report, "payoff_AB")["eligible_blocks"] == 0
    assert primary(report, "payoff_AB")["difference"] is None
    baseline = report["contrasts"][1]["estimates"]["payoff_AB"]
    assert baseline["exclusions"][0]["reasons"]["none"] == ["condition_not_planned"]
