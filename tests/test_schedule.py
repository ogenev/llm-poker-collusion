import json
import random
from pathlib import Path
from typing import cast

import pytest

from poker_collusion.poker import generate_schedule
from poker_collusion.records import DealSchedule


def test_schedule_survives_file_round_trip_and_preserves_matching(tmp_path: Path) -> None:
    schedule = generate_schedule(seed=12, hands=30, initial_rotation=1)
    path = tmp_path / "schedule.json"
    path.write_text(schedule.to_json(), encoding="utf-8")
    loaded = DealSchedule.from_json(path.read_text(encoding="utf-8"))
    assert loaded == schedule
    assert generate_schedule(seed=12, hands=30, initial_rotation=1) == schedule
    assert generate_schedule(seed=13, hands=30, initial_rotation=1) != schedule
    conditions = {
        channel: DealSchedule.from_json(loaded.to_json())
        for channel in ("none", "public", "private")
    }
    for hand_index, deal in enumerate(schedule.deals):
        assert len(set(deal)) == 3
        assert all(0 <= card <= 3 for card in deal)
        expected = dict(zip(schedule.seats_for_hand(hand_index), deal, strict=True))
        for copy in conditions.values():
            actual = dict(zip(copy.seats_for_hand(hand_index), copy.deals[hand_index], strict=True))
            assert actual == expected


@pytest.mark.parametrize("offset", range(3))
def test_seats_are_balanced_each_three_hands(offset: int) -> None:
    schedule = generate_schedule(seed=0, hands=6, initial_rotation=offset)
    for seat in range(3):
        for start in (0, 3):
            assert {schedule.seats_for_hand(h)[seat] for h in range(start, start + 3)} == {
                "A",
                "B",
                "C",
            }
    default = generate_schedule(seed=0, hands=3)
    assert [default.seats_for_hand(h) for h in range(3)] == [
        ("A", "B", "C"),
        ("B", "C", "A"),
        ("C", "A", "B"),
    ]


def test_hand_count_does_not_change_schedule_prefix_or_global_rng() -> None:
    global_state = random.getstate()
    short = generate_schedule(seed=12, hands=3)
    longer = generate_schedule(seed=12, hands=100)
    assert random.getstate() == global_state
    assert longer.deals[:3] == short.deals
    # Detect accidental cycles/permutations through all 24 deals rather than reshuffling.
    assert len(set(longer.deals[:24])) < 24


@pytest.mark.parametrize("hands", [0, -1, True, 1.5])
def test_invalid_hand_counts(hands: object) -> None:
    with pytest.raises(ValueError):
        generate_schedule(seed=0, hands=cast(int, hands))


@pytest.mark.parametrize("index", [-1, 3, True])
def test_invalid_schedule_index(index: int) -> None:
    with pytest.raises(ValueError):
        generate_schedule(seed=0, hands=3).seats_for_hand(index)


@pytest.mark.parametrize(
    "updates",
    [
        {"version": 2},
        {"kind": "poker_hand"},
        {"seed": "12"},
        {"initial_rotation": 3},
        {"initial_rotation": True},
        {"deals": []},
        {"deals": [[0, 0, 1]]},
        {"deals": None},
        {"extra": 1},
    ],
)
def test_invalid_saved_schedule(updates: dict[str, object]) -> None:
    data = json.loads(generate_schedule(seed=12, hands=3).to_json())
    data.update(updates)
    with pytest.raises(ValueError):
        DealSchedule.from_json(json.dumps(data))
