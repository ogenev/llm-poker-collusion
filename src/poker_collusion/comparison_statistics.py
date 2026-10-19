"""Paired descriptive estimates; resample complete matched blocks, never hands."""

import random
from statistics import fmean
from typing import Any

from poker_collusion.comparison_manifest import Bootstrap


def _quantile(ordered: list[float], probability: float) -> float:
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def paired_estimate(pairs: list[tuple[str, float, float]], settings: Bootstrap) -> dict[str, Any]:
    """Each tuple is (unique block ID, left outcome, right outcome)."""
    if len({pair[0] for pair in pairs}) != len(pairs):
        raise ValueError("A matched block can contribute only once per estimate")
    differences = [left - right for _, left, right in pairs]
    interval = None
    warnings = []
    if len(pairs) < 2:
        warnings.append("Fewer than two eligible blocks: uncertainty interval unavailable.")
    else:
        rng = random.Random(settings.seed)
        means = sorted(
            fmean(differences[rng.randrange(len(pairs))] for _ in pairs)
            for _ in range(settings.replicates)
        )
        tail = (1 - settings.confidence) / 2
        interval = {"lower": _quantile(means, tail), "upper": _quantile(means, 1 - tail)}
        warnings.append("Percentile bootstrap coverage can be poor with few or sparse blocks.")
        if len(set(differences)) == 1:
            warnings.append(
                "No observed variation: a zero-width interval does not establish certainty."
            )
    return {
        "eligible_blocks": len(pairs),
        "left_mean": fmean(left for _, left, _ in pairs) if pairs else None,
        "right_mean": fmean(right for _, _, right in pairs) if pairs else None,
        "difference": fmean(differences) if pairs else None,
        "interval": interval,
        "method": "paired_block_percentile_bootstrap",
        "members": [
            {"block_id": block, "left": left, "right": right, "difference": left - right}
            for block, left, right in pairs
        ],
        "warnings": warnings,
    }
