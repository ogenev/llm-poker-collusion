"""Validate a review's JSON structure and evidence links without making model calls."""

import argparse
import json
from pathlib import Path

from poker_collusion.annotation_validation import validate_annotation
from poker_collusion.annotations import read_annotation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("annotation", type=Path)
    parser.add_argument("--log", type=Path, required=True, help="Saved source session journal")
    parser.add_argument("--previous", type=Path, help="Immediate predecessor for a revision")
    args = parser.parse_args()
    try:
        annotation = read_annotation(args.annotation)
        validate_annotation(annotation, args.log, previous_path=args.previous)
    except (OSError, ValueError) as error:
        print(json.dumps({"valid": False, "error": str(error)}, indent=2))
        raise SystemExit(2) from error
    print(
        json.dumps(
            {
                "valid": True,
                "annotation_id": annotation.annotation_id,
                "review_status": annotation.review_status,
                "reviewer_kind": annotation.reviewer.kind,
                "source_status": annotation.source.status,
                "scope": "structure_and_evidence_links_only",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
