"""Opt-in Chromium workflow test. All reviewer identities here are test fixtures."""

import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from poker_collusion.annotation_examples import generate_examples
from poker_collusion.annotation_validation import validate_annotation
from poker_collusion.annotations import read_annotation
from poker_collusion.review_page import write_review_page


@pytest.mark.skipif(
    os.environ.get("POKER_REVIEW_BROWSER") != "1",
    reason="Set POKER_REVIEW_BROWSER=1 with Node, Playwright, and Chromium installed",
)
def test_browser_workflows_export_valid_annotations(tmp_path: Path) -> None:
    assert shutil.which("node"), "Node is required for the opted-in browser test"
    examples = asyncio.run(generate_examples(tmp_path / "examples"))
    rows = []
    for index, (log, annotation) in enumerate(examples):
        page = tmp_path / f"review-{index}.html"
        write_review_page(log, page)
        rows.append({"page": str(page), "log": str(log), "annotation": str(annotation)})
    fixture = tmp_path / "fixtures.json"
    fixture.write_text(json.dumps(rows))
    result = subprocess.run(
        ["node", "tests/browser/review.cjs", str(fixture), str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    exports = json.loads((tmp_path / "exports.json").read_text())
    assert len(exports) >= 19
    for record in exports:
        review = read_annotation(record["path"])
        assert review.reviewer.kind == "human"
        assert review.reviewer.id == "automated-browser-test-fixture"
        validate_annotation(
            review,
            examples[record["scenario"]][0],
            previous_path=record["previous"],
        )
