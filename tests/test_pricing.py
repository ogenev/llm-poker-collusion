import json
from pathlib import Path

import pytest

from poker_collusion.pricing import configure_model_cost

MODEL = "openai/gpt-5.4-mini-2026-03-17"


@pytest.mark.parametrize("value", [-1, True, "1", float("inf"), float("nan"), None, 10**400])
def test_invalid_prices_are_rejected(tmp_path: Path, value: object) -> None:
    rates = {"input": value, "output": 4.5, "input_cache_read": 0.075, "input_cache_write": 0.75}
    path = tmp_path / "prices.json"
    path.write_text(json.dumps({MODEL: rates}))
    with pytest.raises(ValueError):
        configure_model_cost(MODEL, path)


@pytest.mark.parametrize(
    "data", [{}, {MODEL: {}}, {"wrong/model": {}}, {MODEL: {}, "extra/model": {}}]
)
def test_pricing_must_match_the_model_and_schema(tmp_path: Path, data: dict[str, object]) -> None:
    path = tmp_path / "prices.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        configure_model_cost(MODEL, path)
