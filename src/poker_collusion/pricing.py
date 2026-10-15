"""Load explicit per-model prices for Inspect's cost accounting."""

import math
from pathlib import Path

from inspect_ai.model import ModelCost, set_model_cost

from poker_collusion.model_adapter import _read_object


def configure_model_cost(model: str, path: Path) -> None:
    """Read Inspect's JSON pricing format; reject missing, extra, or invalid rates.

    Prices are supplied by the operator, not inferred from a model name. The
    experiment manifest saves the effective rates alongside stopping limits.
    """
    data = _read_object(path.read_text())
    if set(data) != {model}:
        raise ValueError("Pricing must specify exactly the configured model")
    rates = data[model]
    if not isinstance(rates, dict) or set(rates) != {
        "input",
        "output",
        "input_cache_read",
        "input_cache_write",
    }:
        raise ValueError("Expected four per-million-token pricing fields")
    for rate in rates.values():
        try:
            valid = type(rate) in (int, float) and math.isfinite(rate) and rate >= 0
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError("Prices must be finite nonnegative numbers")
    set_model_cost(model, ModelCost(**rates))
