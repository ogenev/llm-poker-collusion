"""Freeze the three-session prospective input cohort and future variants offline."""

import argparse
import asyncio
import json
from pathlib import Path

from poker_collusion.heldout_cohort import seal_cohort
from poker_collusion.pricing import configure_model_cost


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directories", type=Path, nargs=3)
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--model-cost-config", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        configure_model_cost("openai/gpt-6-luna", a.model_cost_config)
        result = asyncio.run(seal_cohort(a.directories, a.policy, a.output))
    except Exception as error:
        p.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
