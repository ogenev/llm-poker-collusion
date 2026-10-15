"""Offline demo: uv run --locked python scripts/demo_session.py --channel private."""

import argparse
import asyncio
import json
from dataclasses import asdict

from poker_collusion.poker import generate_schedule
from poker_collusion.records import Channel, Phase, SessionConfig
from poker_collusion.session import passive_decider, run_session, seeded_random_decider


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a poker session with scripted players")
    parser.add_argument("--channel", choices=[channel.value for channel in Channel], default="none")
    parser.add_argument("--hands", type=int, default=30)
    parser.add_argument("--seed", type=int, default=0, help="Deal schedule seed")
    parser.add_argument("--agent", choices=("passive", "random"), default="random")
    parser.add_argument("--agent-seed", type=int, default=0)
    parser.add_argument("--memory-hands", type=int, default=10)
    args = parser.parse_args()
    try:
        config = SessionConfig(
            hands=args.hands, channel=Channel(args.channel), memory_hands=args.memory_hands
        )
        schedule = generate_schedule(args.seed, config.hands)
    except ValueError as error:
        parser.error(str(error))
    decide = passive_decider if args.agent == "passive" else seeded_random_decider(args.agent_seed)
    state = asyncio.run(run_session(config, schedule, decide))
    print(
        json.dumps(
            {
                "status": state.phase,
                "channel": config.channel,
                "completed_hands": state.completed_hands,
                "rewards": state.rewards,
                "retained_hands": {
                    player: len(history) for player, history in state.histories.items()
                },
                "last_hand_message_count": len(state.messages),
                "failure": asdict(state.failure) if state.failure else None,
            },
            indent=2,
        )
    )
    if state.phase != Phase.COMPLETE:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
