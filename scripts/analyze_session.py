"""Analyse one saved session and selected annotation without making model calls."""

import argparse
import asyncio
import json
from pathlib import Path

from poker_collusion.analysis import analyze_session, write_analysis


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="Stable saved session journal")
    parser.add_argument("--annotation", type=Path, help="Explicitly selected review; optional")
    parser.add_argument("--previous", type=Path, help="Immediate predecessor for a revision")
    parser.add_argument("--output", type=Path, required=True, help="New analysis JSON file")
    args = parser.parse_args()
    try:
        result = asyncio.run(
            analyze_session(args.log, annotation_path=args.annotation, previous_path=args.previous)
        )
        write_analysis(args.output, result)
    except (OSError, ValueError) as error:
        print(json.dumps({"analyzed": False, "error": str(error)}, indent=2))
        raise SystemExit(2) from error
    print(
        json.dumps(
            {
                "analyzed": True,
                "output": str(args.output),
                "session_id": result.source.session_id,
                "source_status": result.source.status,
                "replay_verified": result.session.replay_verified,
                "review_status": None if result.review is None else result.review.review_status,
                "reviewer_kind": None if result.review is None else result.review.reviewer.kind,
                "scope": "single_session_descriptive",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
