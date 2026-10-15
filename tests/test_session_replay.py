import asyncio
import json
from pathlib import Path
from typing import Any, cast

import pytest

from poker_collusion.event_log import JsonlRecorder, read_log
from poker_collusion.poker import generate_schedule
from poker_collusion.records import (
    Action,
    BetDecision,
    Channel,
    Decision,
    MessageDecision,
    PassDecision,
    Phase,
    PlayerView,
    SessionConfig,
    SessionState,
)
from poker_collusion.replay import IncompleteLogError, ReplayError, replay_session
from poker_collusion.serialization import digest
from poker_collusion.session import passive_decider, run_session, seeded_random_decider
from poker_collusion.session_audit import Decider


def record(path: Path, config: SessionConfig, decide: Decider = passive_decider) -> SessionState:
    with JsonlRecorder(path) as recorder:
        return asyncio.run(
            run_session(
                config,
                generate_schedule(17, config.hands, initial_rotation=2),
                decide,
                recorder=recorder,
            )
        )


@pytest.mark.parametrize("channel", list(Channel))
@pytest.mark.parametrize("memory_hands", [0, 1, 10])
@pytest.mark.parametrize("budget", [0, 30, 1000])
def test_complete_sessions_replay_all_state(
    tmp_path: Path,
    channel: Channel,
    memory_hands: int,
    budget: int,
) -> None:
    path = tmp_path / "complete.jsonl"
    config = SessionConfig(
        hands=12, channel=channel, memory_hands=memory_hands, message_budget_chars=budget
    )
    original = record(path, config, seeded_random_decider(41))
    replayed = asyncio.run(replay_session(path))
    assert original == replayed
    assert replayed.phase == Phase.COMPLETE
    assert replayed.completed_hands == 12
    assert read_log(path).status == "complete"
    replayed.rewards["A"] += 10
    assert original != replayed


@pytest.mark.parametrize("channel", [Channel.PUBLIC, Channel.PRIVATE])
@pytest.mark.parametrize("finish_order", [("A", "B", "C"), ("C", "B", "A")])
def test_replay_preserves_response_order_without_changing_delivery(
    tmp_path: Path,
    channel: Channel,
    finish_order: tuple[str, ...],
) -> None:
    path = tmp_path / "ordered.jsonl"

    async def scenario() -> SessionState:
        gates = {
            (hand, round_, player): asyncio.Event()
            for hand in range(2)
            for round_ in range(2)
            for player in finish_order
        }

        async def decide(view: PlayerView) -> Decision:
            if view.phase == Phase.BETTING:
                return await passive_decider(view)
            assert view.round_index is not None
            index = finish_order.index(view.player_id)
            if index:
                await gates[(view.hand_index, view.round_index, finish_order[index - 1])].wait()
            gates[(view.hand_index, view.round_index, view.player_id)].set()
            return MessageDecision(
                "🂡 message ", view.private_recipients[0] if channel == Channel.PRIVATE else None
            )

        with JsonlRecorder(path) as recorder:
            original = await run_session(
                SessionConfig(hands=2, channel=channel),
                generate_schedule(8, 2),
                decide,
                recorder=recorder,
            )
        assert await asyncio.wait_for(replay_session(path), 2) == original
        return original

    state = asyncio.run(scenario())
    assert [message.sender for message in state.messages] == ["A", "B", "C"] * 2
    events = read_log(path).events
    requested = {
        e.data["request_id"]: e.data["view"] for e in events if e.event == "decision_requested"
    }
    returned = [requested[e.data["request_id"]] for e in events if e.event == "decision_returned"]
    assert [cast(dict[str, object], view)["player_id"] for view in returned[:3]] == list(
        finish_order
    )


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        {"text": "unparsed"},
        ["invalid"],
        PassDecision(),
        BetDecision(Action.CALL),
        BetDecision(cast(Action, "check")),
        MessageDecision("hello"),
        float("nan"),
    ],
)
def test_invalid_betting_replays_without_turning_string_action_into_enum(
    tmp_path: Path,
    invalid: object,
) -> None:
    path = tmp_path / "failed.jsonl"

    async def decide(view: PlayerView) -> Decision:
        if view.hand_index == 1:
            return cast(Decision, invalid)
        return await passive_decider(view)

    original = record(path, SessionConfig(hands=3), decide)
    assert original.phase == Phase.FAILED
    assert original.completed_hands == 1
    assert read_log(path).status == "failed"
    assert asyncio.run(replay_session(path)) == original


@pytest.mark.parametrize(
    "invalid",
    [
        MessageDecision("hello"),
        MessageDecision("hello", "A"),
        MessageDecision("hello", "D"),
        MessageDecision(" " * 10, "B"),
        MessageDecision("x" * 501, "B"),
        MessageDecision(cast(str, 42), "B"),
        MessageDecision("hi", cast(str, ["B", "C"])),
        BetDecision(Action.BET),
        None,
    ],
)
def test_invalid_communication_preserves_valid_pending_messages(
    tmp_path: Path,
    invalid: object,
) -> None:
    path = tmp_path / "failed-round.jsonl"

    async def decide(view: PlayerView) -> Decision:
        if view.player_id == "A":
            return cast(Decision, invalid)
        return MessageDecision("accepted but not delivered", "A")

    original = record(path, SessionConfig(hands=2, channel=Channel.PRIVATE), decide)
    assert original.phase == Phase.FAILED
    assert len(original.pending_messages) == 2
    assert not original.messages
    assert asyncio.run(replay_session(path)) == original


@pytest.mark.parametrize("channel", list(Channel))
@pytest.mark.parametrize("timeout", [False, True])
def test_callback_errors_and_timeouts_replay_without_waiting(
    tmp_path: Path,
    channel: Channel,
    timeout: bool,
) -> None:
    path = tmp_path / "provider-failure.jsonl"

    async def decide(view: PlayerView) -> Decision:
        if timeout:
            await asyncio.Event().wait()
        raise RuntimeError("provider unavailable")

    original = record(
        path, SessionConfig(hands=2, channel=channel, decision_timeout_seconds=0.01), decide
    )
    assert original.phase == Phase.FAILED
    assert asyncio.run(replay_session(path)) == original


def rewrite(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


@pytest.mark.parametrize(
    "event_name,field",
    [
        ("decision_requested", "view"),
        ("action_applied", "poker_snapshot"),
        ("messages_delivered", "budgets"),
        ("rewards_settled", "rewards"),
        ("memory_updated", "histories"),
        ("session_ended", "state"),
    ],
)
def test_replay_detects_tampered_observations_effects_and_final_state(
    tmp_path: Path,
    event_name: str,
    field: str,
) -> None:
    path = tmp_path / "tampered.jsonl"
    record(path, SessionConfig(hands=2, channel=Channel.PRIVATE), seeded_random_decider(0))
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    row = next(row for row in rows if row["event"] == event_name)
    if field == "state":
        row["data"][field]["rewards"]["A"] += 100
    elif field == "view":
        row["data"][field]["poker"]["own_card"] = "FAKE"
    else:
        row["data"][field] = "tampered"
    rewrite(path, rows)
    with pytest.raises(ReplayError, match="differs"):
        asyncio.run(replay_session(path))


@pytest.mark.parametrize(
    "mutation",
    [
        "version",
        "bool_version",
        "config_version",
        "extra_config",
        "config_hash",
        "schedule_hash",
        "gap",
        "duplicate",
        "wrong_session",
        "unknown_event",
        "after_footer",
        "duplicate_result",
        "missing_result",
        "state_version",
        "malformed_line",
        "nonfinite",
        "duplicate_json_key",
    ],
)
def test_reader_rejects_corrupt_or_incompatible_journals(tmp_path: Path, mutation: str) -> None:
    path = tmp_path / "corrupt.jsonl"
    record(path, SessionConfig(hands=1))
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if mutation == "version":
        rows[0]["version"] = 2
    elif mutation == "bool_version":
        rows[0]["version"] = True
    elif mutation in ("config_version", "extra_config"):
        rows[0]["data"]["config"]["version" if mutation == "config_version" else "extra"] = 2
        rows[0]["data"]["config_sha256"] = digest(rows[0]["data"]["config"])
    elif mutation in ("config_hash", "schedule_hash"):
        rows[0]["data"]["config_sha256" if mutation == "config_hash" else "schedule_sha256"] = "bad"
    elif mutation == "gap":
        rows.pop(2)
    elif mutation == "duplicate":
        rows.insert(2, rows[2])
    elif mutation == "wrong_session":
        rows[3]["session_id"] = "different"
    elif mutation == "unknown_event":
        rows[3]["event"] = "future_event"
    elif mutation == "after_footer":
        rows.append(rows[-1])
    elif mutation == "state_version":
        rows[-1]["data"]["state"]["version"] = 2
    elif mutation in ("duplicate_result", "missing_result"):
        resolved = next(
            index for index, row in enumerate(rows) if row["event"] == "decision_resolved"
        )
        if mutation == "duplicate_result":
            rows.insert(resolved, rows[resolved].copy())
        else:
            rows.pop(resolved)
        for sequence, row in enumerate(rows):
            row["sequence"] = sequence
    rewrite(path, rows)
    if mutation == "malformed_line":
        path.write_text(path.read_text().replace('"event":', '"event" BROKEN:', 1))
    elif mutation == "nonfinite":
        path.write_text(
            path.read_text().replace('"protocol_version": 1', '"protocol_version": NaN', 1)
        )
    elif mutation == "duplicate_json_key":
        path.write_text(
            path.read_text().replace('"sequence": 0', '"sequence": 0, "sequence": 0', 1)
        )
    with pytest.raises(ValueError):
        read_log(path)


@pytest.mark.parametrize("tail", [b"", b'{"kind":', b"\xff\xfe", b'{"valid":true}'])
def test_incomplete_prefix_is_inspectable_and_excluded_from_replay(
    tmp_path: Path,
    tail: bytes,
) -> None:
    path = tmp_path / "partial.jsonl"
    record(path, SessionConfig(hands=2))
    lines = path.read_bytes().splitlines(keepends=True)
    prefix = b"".join(lines[:10])
    path.write_bytes(prefix + tail)
    log = read_log(path)
    assert log.status == "incomplete"
    assert len(log.events) == 10
    assert log.trailing_bytes == len(tail)
    with pytest.raises(IncompleteLogError):
        asyncio.run(replay_session(path))
    assert path.read_bytes() == prefix + tail


def test_empty_journal_is_incomplete(tmp_path: Path) -> None:
    path = tmp_path / "empty.jsonl"
    path.touch()
    assert read_log(path).status == "incomplete"
    with pytest.raises(IncompleteLogError):
        asyncio.run(replay_session(path))


@pytest.mark.parametrize(
    "candidate",
    [
        {"type": "BetDecision", "fields": None},
        {"type": "BetDecision", "fields": []},
        {"type": "BetDecision", "fields": {"extra": 42}},
        {"type": "dict", "items": [[{"type": "list", "items": []}, None]]},
        {"type": "list", "items": 42},
        {"type": "int", "value": True},
        {"type": "Action", "value": "invalid"},
        {"type": "unknown"},
    ],
)
def test_malformed_candidate_records_fail_explicitly(tmp_path: Path, candidate: object) -> None:
    path = tmp_path / "bad-candidate.jsonl"
    record(path, SessionConfig(hands=1))
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    row = next(row for row in rows if row["event"] == "decision_returned")
    row["data"]["candidate"] = candidate
    rewrite(path, rows)
    with pytest.raises(ReplayError):
        asyncio.run(replay_session(path))
