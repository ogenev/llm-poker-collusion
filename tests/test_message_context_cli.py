import json
import runpy
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.usefixtures("inspect_runtime")


@pytest.mark.parametrize("offline", [True, False])
def test_context_preflight_never_generates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    offline: bool,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "offline-preflight-fixture")
    args = [
        "scripts/check_message_context.py",
        "configs/qualification-message-context-gpt-6-luna-medium-strict.json",
        "--preflight",
        "--output",
        str(tmp_path / "unused"),
    ]
    args += (
        ["--offline"]
        if offline
        else ["--model-cost-config", "configs/openai-gpt-6-luna-cycle2-pricing.json"]
    )
    monkeypatch.setattr(sys, "argv", args)
    runpy.run_path(args[0], run_name="__main__")
    report = json.loads(capsys.readouterr().out)
    assert report["api_calls"] == 0 and report["mock"] == offline
    assert report["plan"]["maximum_decision_calls"] == 60
    assert not (tmp_path / "unused").exists()


def test_context_cli_requires_fresh_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scripts/check_message_context.py",
            "configs/qualification-message-context-gpt-6-luna-medium-strict.json",
            "--offline",
        ],
    )
    with pytest.raises(SystemExit) as error:
        runpy.run_path(sys.argv[0], run_name="__main__")
    assert error.value.code == 2
