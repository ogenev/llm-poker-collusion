"""Prepare a condition-masked coding packet or validate explicit assistant rank codes."""

import argparse
import asyncio
import json
from pathlib import Path

from poker_collusion.honesty_probe_scoring import coding_packet, score_packet
from poker_collusion.pricing import configure_model_cost


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("screen", type=Path)
    p.add_argument("completion", type=Path)
    p.add_argument("--model-cost-config", required=True, type=Path)
    p.add_argument("--codes", type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    try:
        configure_model_cost("openai/gpt-6-luna", a.model_cost_config)
        result = asyncio.run(
            score_packet(a.screen, a.completion, json.loads(a.codes.read_text()))
            if a.codes
            else coding_packet(a.screen, a.completion)
        )
        with a.output.open("x") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
    except Exception as error:
        p.error(str(error))
    print(
        json.dumps(
            {
                "output": str(a.output),
                "responses": len(result["responses"]),
                "paid_calls": 0,
                "human_annotations": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
