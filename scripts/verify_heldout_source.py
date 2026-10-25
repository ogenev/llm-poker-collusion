"""Verify one source session and its before-response selection receipts offline."""

import argparse
import asyncio
import json
from pathlib import Path

from poker_collusion.heldout_source_verify import verify_source
from poker_collusion.pricing import configure_model_cost


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--model-cost-config", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        configure_model_cost("openai/gpt-6-luna", a.model_cost_config)
        result = asyncio.run(verify_source(a.directory, a.policy))
        with a.output.open("x") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
    except Exception as error:
        p.error(str(error))
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "output": str(a.output),
                "paid_calls": 0,
                "contexts": result.get("selection", {}).get("selected_contexts"),
            }
        )
    )
    if not result["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
