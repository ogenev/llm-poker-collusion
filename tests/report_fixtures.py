"""Saved preparation reports for renderer tests; no human judgments or live calls."""

import asyncio
import json
import socket
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from test_comparison import review_path, with_label

from poker_collusion.annotations import ReviewStatus, Verdict, annotation_to_json, read_annotation
from poker_collusion.comparison import compare_sessions, write_comparison
from poker_collusion.comparison_example import generate_comparison_example

ATTACK = (
    "</script><script>globalThis.injected=1</script>"
    '<img src=x onerror="globalThis.injected=1">@@SCRIPT@@ & \u2028'
)


@pytest.fixture(scope="module")
def report_cases(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("report-fixtures")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("XDG_DATA_HOME", str(root / "data"))
        patch.setenv("XDG_CACHE_HOME", str(root / "cache"))
        connect = socket.socket.connect

        def offline(sock: socket.socket, address: Any) -> None:
            if sock.family in (socket.AF_INET, socket.AF_INET6):
                raise AssertionError("Report fixtures must remain offline")
            connect(sock, address)

        patch.setattr(socket.socket, "connect", offline)
        manifest = asyncio.run(generate_comparison_example(root / "example"))
        base = root / "base.json"
        write_comparison(base, asyncio.run(compare_sessions(manifest)))
        with_label(review_path(manifest), Verdict.OBSERVED)
        with_label(review_path(manifest, "block-1-private"), Verdict.UNCERTAIN)
        path = review_path(manifest, "block-2-public")
        review = read_annotation(path)
        path.write_text(annotation_to_json(replace(review, review_status=ReviewStatus.DRAFT)))
        path = review_path(manifest)
        review = read_annotation(path)
        path.write_text(
            annotation_to_json(
                replace(
                    review,
                    reviewer=replace(review.reviewer, id=ATTACK),
                    pair_reviews=tuple(
                        replace(pair, explanation=ATTACK) for pair in review.pair_reviews
                    ),
                )
            )
        )
        source = read_annotation(review_path(manifest, "block-0-none")).source
        game = manifest.parent / "run" / "sessions" / source.session_id / "session.jsonl"
        game.rename(game.with_suffix(".unavailable"))
        review_path(manifest, "block-1-none").rename(root / "unselected.json")
        mixed = root / "mixed.json"
        write_comparison(mixed, asyncio.run(compare_sessions(manifest)))
        selection = json.loads(manifest.read_text())
        selection["runs"][0]["reviews"] = []
        manifest.write_text(json.dumps(selection))
        empty = root / "unreviewed.json"
        write_comparison(empty, asyncio.run(compare_sessions(manifest)))
    return {"base": base, "mixed": mixed, "unreviewed": empty, "manifest": manifest}
