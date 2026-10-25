import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from poker_collusion.honesty_probe import HonestyConfig
from poker_collusion.honesty_probe_approval import require_approval
from poker_collusion.honesty_probe_run import run_honesty
from poker_collusion.honesty_probe_verify import verify_honesty
from poker_collusion.inspect_transport import configured_model
from poker_collusion.pricing import configure_model_cost
from poker_collusion.serialization import canonical

pytestmark = pytest.mark.usefixtures("inspect_runtime")


def test_sdk_payloads_behavioral_negatives_and_tampering(tmp_path: Path) -> None:
    settings = HonestyConfig.from_json(
        Path("configs/probe-honesty-gpt-6-luna-medium-strict-cycle4-screen.json").read_text()
    )
    configure_model_cost(
        settings.model.model, Path("configs/openai-gpt-6-luna-cycle4-pricing.json")
    )
    requests: list[dict[str, Any]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        assert body["reasoning_effort"] == "medium"
        assert body["max_completion_tokens"] == 4096 and body["n"] == 1
        assert "temperature" not in body and "tools" not in body
        assert body["response_format"]["json_schema"]["strict"] is True
        view = json.loads(body["messages"][1]["content"])
        false_rank = next(c for c in "JQKA" if c != view["poker"]["own_card"])
        content = canonical(
            {
                "decision": {
                    "type": "message",
                    "recipient": view["private_recipients"][0],
                    "text": f"I have {false_rank}.",
                }
            }
        )
        return httpx.Response(
            200,
            json={
                "id": f"offline-{len(requests)}",
                "object": "chat.completion",
                "created": 1,
                "model": body["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 300, "completion_tokens": 10, "total_tokens": 310},
            },
        )

    async def run() -> dict[str, Any]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            model = configured_model(
                settings.model,
                1,
                api_key="offline-http-fixture",
                base_url="https://api.openai.com/v1",
                http_client=client,
            )
            with pytest.raises(ValueError, match="authorization"):
                await run_honesty(settings, tmp_path / "unapproved", model=model)
            assert not requests and not (tmp_path / "unapproved").exists()
            return await run_honesty(
                settings,
                tmp_path / "screen",
                model=model,
                authorization={"test": "Intercepted HTTP; no live approval"},
            )

    summary = asyncio.run(run())
    assert summary["result"] == "complete" and len(requests) == 12
    assert summary["usable_responses"] == 12  # Lies remain usable research observations.
    assert asyncio.run(verify_honesty(tmp_path / "screen"))["passed"]
    journal = tmp_path / "screen" / "model.jsonl"
    rows = [json.loads(s) for s in journal.read_text().splitlines()]
    rows[2]["data"]["model_events"][0]["call"]["request"]["reasoning_effort"] = "low"
    journal.write_text("\n".join(canonical(r) for r in rows) + "\n")
    with pytest.raises(ValueError, match="Inspect/provider evidence"):
        asyncio.run(verify_honesty(tmp_path / "screen"))


def test_approval_binds_files_budget_and_single_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Path(
        "configs/probe-honesty-gpt-6-luna-medium-strict-cycle4-screen.json"
    ).read_bytes()
    (tmp_path / "config.json").write_bytes(original)
    (tmp_path / "prices.json").write_text("{}")
    manifest = {
        "frozen_files": {"config.json": hashlib.sha256(original).hexdigest()},
        "stage_configs": {"screen": "config.json"},
        "pricing_file": "prices.json",
        "live_outputs": {"screen": "screen"},
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(canonical(manifest))
    approval: dict[str, Any] = {
        "approved": False,
        "user_message": "test only",
        "approved_at": "test only",
        "maximum_calls": 120,
        "sum_cost_thresholds_usd": 0.5,
        "sum_token_thresholds": 1_000_000,
        "preparation_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }
    approval_path = tmp_path / "approval.json"
    monkeypatch.chdir(tmp_path)

    def check(output: str = "screen") -> dict[str, Any]:
        approval_path.write_text(canonical(approval))
        return require_approval(
            approval_path,
            manifest_path,
            config_path=Path("config.json"),
            pricing_path=Path("prices.json"),
            output=Path(output),
            previous_run=None,
        )

    with pytest.raises(ValueError, match="Explicit approval"):
        check()
    approval["approved"] = True
    assert check()["approval_sha256"]
    with pytest.raises(ValueError, match="fresh output"):
        check("replacement")
    (tmp_path / "screen").mkdir()
    with pytest.raises(ValueError, match="fresh output"):
        check()
    (tmp_path / "config.json").write_bytes(original + b"\n")
    with pytest.raises(ValueError, match="Frozen preparation changed"):
        check()
