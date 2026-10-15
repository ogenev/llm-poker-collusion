"""Offline verification: uv run --locked python scripts/replay_session.py LOG.jsonl."""

import argparse
import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from poker_collusion.event_log import read_log
from poker_collusion.replay import replay_session


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify a recorded poker session without model calls"
    )
    parser.add_argument("log", type=Path)
    parser.add_argument(
        "--inspect", action="store_true", help="Inspect status/prefix without replay"
    )
    args = parser.parse_args()
    try:
        log = read_log(args.log)
        summary: dict[str, object] = {
            "session_id": log.session_id,
            "status": log.status,
            "events": len(log.events),
            "trailing_bytes": log.trailing_bytes,
            "verified": False,
        }
        if not args.inspect:
            state = asyncio.run(replay_session(args.log))
            summary.update(
                verified=True,
                completed_hands=state.completed_hands,
                rewards=state.rewards,
                failure=asdict(state.failure) if state.failure else None,
            )
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
