"""Opt-in browser checks for the standalone comparison viewer."""

import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from inspect_ai.model import ChatMessage, GenerateConfig, ModelOutput, get_model
from inspect_ai.tool import ToolChoice, ToolInfo
from report_fixtures import report_cases as report_cases

from poker_collusion.comparison import compare_sessions, write_comparison
from poker_collusion.experiment import run_experiment
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.model_adapter import ModelConfig
from poker_collusion.offline_model import offline_model, scripted_output
from poker_collusion.records import SessionConfig
from poker_collusion.report_page import write_report
from poker_collusion.review_page import write_review_page


@pytest.mark.skipif(
    os.environ.get("POKER_REPORT_BROWSER") != "1",
    reason="Set POKER_REPORT_BROWSER=1 with Node, Playwright, and Chromium installed",
)
@pytest.mark.usefixtures("inspect_runtime")
def test_report_browser_filters_evidence_links_layout_and_fixed_estimates(
    report_cases: dict[str, Path], tmp_path: Path
) -> None:
    assert shutil.which("node"), "Node is required for the opted-in browser test"
    fixtures = []
    mixed = json.loads(report_cases["mixed"].read_text())
    session = next(s for s in mixed["sessions"] if s["sample_id"] == "block-0-private")
    sid = session["analysis"]["source"]["session_id"]
    game = report_cases["manifest"].parent / "run" / "sessions" / sid / "session.jsonl"
    source_page = tmp_path / "source review.html"
    write_review_page(game, source_page)
    links = tmp_path / "links.json"
    links.write_text(json.dumps({sid: source_page.name}))
    for case in ("base", "mixed", "unreviewed"):
        page = tmp_path / f"{case}.html"
        write_report(report_cases[case], page, review_pages_path=links if case == "mixed" else None)
        fixtures.append({"case": case, "path": str(page)})

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

    for case in ("large", "failed"):
        config = ExperimentConfig(
            ModelConfig("mockllm/model"),
            SessionConfig(hands=1),
            seeds=tuple(range(10)) if case == "large" else (0,),
        )
        model = (
            offline_model()
            if case == "large"
            else get_model("mockllm/model", custom_outputs=broken, memoize=False)
        )
        asyncio.run(run_experiment(config, tmp_path / case, model=model))
        manifest = tmp_path / f"{case}.manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "kind": "session_comparison",
                    "version": 1,
                    "dataset_role": "preparation",
                    "reviewer_kind": "human",
                    "bootstrap": {"replicates": 100, "seed": 0, "confidence": 0.95},
                    "runs": [{"directory": case, "reviews": []}],
                }
            )
        )
        data = tmp_path / f"{case}.json"
        write_comparison(data, asyncio.run(compare_sessions(manifest)))
        page = tmp_path / f"{case}.html"
        write_report(data, page)
        fixtures.append({"case": case, "path": str(page)})
    fixture = tmp_path / "browser-fixtures.json"
    fixture.write_text(json.dumps({"reports": fixtures, "source_page": str(source_page)}))
    result = subprocess.run(
        ["node", "tests/browser/report.cjs", str(fixture), str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
