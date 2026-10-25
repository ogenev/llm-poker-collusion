"""Prospective, response-independent selection from frozen communication-round views."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Any, Self, cast

from poker_collusion.durable_jsonl import DurableJsonl
from poker_collusion.event_log import JsonlRecorder
from poker_collusion.history_context import source_view
from poker_collusion.prompts import render_prompt
from poker_collusion.records import PLAYER_IDS, Phase, PlayerView
from poker_collusion.serialization import canonical, digest

POLICY_SHA256 = "14c7bb8073d874e4a3b31143f196ced244fd05eda83e5602ea84897871d7fe0d"


def load_policy(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != POLICY_SHA256:
        raise ValueError("Cycle5 selection policy differs from the frozen protocol")
    return cast(dict[str, Any], json.loads(raw))


class ContextSelector:
    """See requested views only; no response, payoff or outcome input is accepted."""

    def __init__(self, policy: dict[str, Any], seed: int) -> None:
        if seed not in policy["seeds"]:
            raise ValueError("Unexpected source seed")
        self.policy, self.seed = policy, seed
        self.patterns = tuple(re.compile(s, re.IGNORECASE) for s in policy["patterns"])
        self.pending: list[tuple[int, int, PlayerView]] = []
        self.selected = 0

    def requested(self, request_id: int, sequence: int, view: PlayerView) -> dict[str, Any] | None:
        if view.phase != Phase.COMMUNICATION or view.round_index != 1:
            return None
        self.pending.append((request_id, sequence, view))
        if len(self.pending) != 3:
            return None
        batch, self.pending = self.pending, []
        if [v.player_id for _, _, v in batch] != list(PLAYER_IDS) or len(
            {v.hand_index for _, _, v in batch}
        ) != 1:
            raise ValueError("Expected all three frozen views before second-round responses")
        if (
            view.hand_index + 1 < self.policy["minimum_hand"]
            or self.selected >= self.policy["maximum_contexts_per_session"]
        ):
            return None
        offset = (2 * self.seed + 2 * view.hand_index) % 3
        order = PLAYER_IDS[offset:] + PLAYER_IDS[:offset]
        for player in order:
            request, seq, candidate = next(item for item in batch if item[2].player_id == player)
            for message in candidate.messages:
                text = message.text.replace("’", "'")
                if (
                    message.round_index != 0
                    or message.recipient != candidate.player_id
                    or message.sender == candidate.player_id
                    or not any(pattern.search(text) for pattern in self.patterns)
                ):
                    continue
                self.selected += 1
                prompt = render_prompt(candidate, response_format="strict_json_schema")
                return {
                    "context_id": f"seed-{self.seed}-context-{self.selected}",
                    "seed": self.seed,
                    "selection_index": self.selected,
                    "hand": candidate.hand_index + 1,
                    "request_id": request,
                    "view_sequence": seq,
                    "requester": message.sender,
                    "recipient": candidate.player_id,
                    "focal_message": json.loads(canonical(message)),
                    "view": json.loads(canonical(candidate)),
                    "original_prompt_sha256": prompt.sha256,
                    "rule": "First eligible hands; one per hand; rotated recipient priority",
                }
        return None


class SelectionRecorder:
    """Forward unchanged native events, then fsync selection before callbacks can run."""

    def __init__(self, base: JsonlRecorder, policy_path: Path, seed: int) -> None:
        self.base = base
        self.policy = load_policy(policy_path)
        self.selector = ContextSelector(self.policy, seed)
        self.writer = DurableJsonl(base.path.with_name("selection.jsonl"))
        self.sequence = 0
        self.writer.write(
            {
                "event": "started",
                "kind": "prospective_selection",
                "version": 1,
                "session_id": base.session_id,
                "seed": seed,
                "policy_sha256": POLICY_SHA256,
                "policy": self.policy,
                "human_annotations": 0,
            }
        )

    def emit(self, event: str, data: dict[str, object]) -> None:
        self.base.emit(event, data)
        if event == "decision_requested":
            view = cast(PlayerView, data["view"])
            result = self.selector.requested(cast(int, data["request_id"]), self.sequence, view)
            if result is not None:
                prefix = self.base.path.read_bytes()
                self.writer.write(
                    {
                        "event": "selected",
                        **result,
                        "session_id": self.base.session_id,
                        "recorded_at": datetime.now(UTC).isoformat(),
                        "prefix_bytes": len(prefix),
                        "prefix_last_sequence": self.sequence,
                        "prefix_sha256": hashlib.sha256(prefix).hexdigest(),
                    }
                )
        if event == "session_ended":
            self.writer.write({"event": "ended", "selected_contexts": self.selector.selected})
        self.sequence += 1

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.writer.__exit__(exc_type, exc, traceback)


def verify_selection(directory: Path, policy_path: Path, seed: int) -> dict[str, Any]:
    """Recompute selection using requested views and prove each saved prefix precedes replies."""
    policy = load_policy(policy_path)
    selector = ContextSelector(policy, seed)
    raw = (directory / "session.jsonl").read_bytes()
    lines = raw.splitlines(keepends=True)
    if not lines or not all(line.endswith(b"\n") for line in lines):
        raise ValueError("Incomplete source journal; preserve partial attempt")
    game = [json.loads(line) for line in lines]
    receipt_raw = (directory / "selection.jsonl").read_bytes()
    if not receipt_raw.endswith(b"\n"):
        raise ValueError("Uncommitted selection receipt tail")
    receipts = [json.loads(s) for s in receipt_raw.splitlines()]
    header = receipts[0]
    if header != {
        "event": "started",
        "kind": "prospective_selection",
        "version": 1,
        "session_id": game[0]["session_id"],
        "seed": seed,
        "policy_sha256": POLICY_SHA256,
        "policy": policy,
        "human_annotations": 0,
    }:
        raise ValueError("Selection header differs")
    expected = []
    for row in game:
        if row["event"] == "decision_requested":
            found = selector.requested(
                row["data"]["request_id"], row["sequence"], source_view(row["data"]["view"])
            )
            if found is not None:
                expected.append((found, row["sequence"]))
    selected = [r for r in receipts if r["event"] == "selected"]
    if len(receipts) != len(selected) + 2 or len(selected) != len(expected):
        raise ValueError("Selected coverage differs; no quota backfill or omission")
    if receipts[-1] != {"event": "ended", "selected_contexts": len(expected)}:
        raise ValueError("Incomplete selection footer")
    model = [json.loads(s) for s in (directory / "model.jsonl").read_text().splitlines()]
    starts = {r["data"]["request_id"]: r["data"] for r in model if r["event"] == "call_started"}
    for saved, (wanted, boundary) in zip(selected, expected, strict=True):
        prefix = b"".join(lines[: boundary + 1])
        expected_saved = {
            "event": "selected",
            **wanted,
            "session_id": game[0]["session_id"],
            "recorded_at": saved["recorded_at"],
            "prefix_bytes": len(prefix),
            "prefix_last_sequence": boundary,
            "prefix_sha256": hashlib.sha256(prefix).hexdigest(),
        }
        if saved != expected_saved or raw[: saved["prefix_bytes"]] != prefix:
            raise ValueError("Selection/committed prefix differs")
        selected_time = datetime.fromisoformat(saved["recorded_at"])
        started_time = datetime.fromisoformat(starts[wanted["request_id"]]["timestamp"])
        if selected_time.tzinfo is None or selected_time > started_time:
            raise ValueError("Selection was not frozen before the selected model call")
        current_round_ids = {
            row["data"]["request_id"]
            for row in game[: boundary + 1]
            if row["event"] == "decision_requested"
            and row["data"]["view"]["hand_index"] == wanted["hand"] - 1
            and row["data"]["view"]["round_index"] == 1
        }
        if len(current_round_ids) != 3 or any(
            selected_time > datetime.fromisoformat(starts[request]["timestamp"])
            for request in current_round_ids
        ):
            raise ValueError("Selection must precede all three current-round model calls")
        if any(
            row["event"] in ("decision_returned", "decision_resolved")
            and row["data"]["request_id"] in current_round_ids
            for row in game[: boundary + 1]
        ):
            raise ValueError("Selection prefix contains a current-round response")
    return {
        "passed": True,
        "seed": seed,
        "selected_contexts": len(selected),
        "contexts": selected,
        "policy_sha256": POLICY_SHA256,
        "selection_receipt_sha256": digest(receipts),
        "source_session_sha256": hashlib.sha256(raw).hexdigest(),
        "source_model_sha256": hashlib.sha256((directory / "model.jsonl").read_bytes()).hexdigest(),
        "human_annotations": 0,
        "paid_verification_calls": 0,
        "scope": (
            "Operational matcher/selection integrity, not independent semantic or coalition review"
        ),
    }
