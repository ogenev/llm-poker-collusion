import hashlib
import json
import stat
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest
from report_fixtures import ATTACK
from report_fixtures import report_cases as report_cases

from poker_collusion.report_page import render_report, write_report
from poker_collusion.report_validation import read_comparison_report
from poker_collusion.review_page import write_review_page


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.payload = ""
        self.active = False
        self.scripts = 0
        self.external: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "script":
            self.scripts += 1
            self.active = attributes.get("id") == "report-data"
        for key in ("href", "src"):
            value = attributes.get(key)
            if value and not value.startswith("#"):
                self.external.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.active = False

    def handle_data(self, data: str) -> None:
        if self.active:
            self.payload += data


@pytest.mark.parametrize("case", ["base", "mixed", "unreviewed"])
def test_report_preserves_exact_saved_results_and_source_hash(
    report_cases: dict[str, Path], case: str
) -> None:
    source = report_cases[case]
    raw = source.read_bytes()
    html = render_report(source)
    parsed = PageParser()
    parsed.feed(html)
    embedded = json.loads(parsed.payload)
    assert parsed.scripts == 2 and not parsed.external
    assert embedded["report"] == json.loads(raw)
    assert embedded["report_sha256"] == hashlib.sha256(raw).hexdigest()
    assert embedded["review_pages"] == {}
    assert "connect-src 'none'" in html
    assert render_report(source) == html and source.read_bytes() == raw
    if case == "mixed":
        assert ATTACK not in html and ATTACK in parsed.payload.replace("\\u003c", "<").replace(
            "\\u003e", ">"
        ).replace("\\u0026", "&").replace("\\u2028", "\u2028").replace('\\"', '"')


def test_private_exclusive_output_and_cli(report_cases: dict[str, Path], tmp_path: Path) -> None:
    source, output = report_cases["mixed"], tmp_path / "report.html"
    command = [sys.executable, "scripts/render_report.py", str(source), "--output", str(output)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["offline"]
    original = output.read_bytes()
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert subprocess.run(command, capture_output=True).returncode == 2
    assert output.read_bytes() == original
    with pytest.raises(FileExistsError):
        write_report(source, source)
    malformed = tmp_path / "malformed.json"
    malformed.write_text('{"kind": "session_comparison_analysis"}')
    command[2] = str(malformed)
    command[-1] = str(tmp_path / "invalid.html")
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 2 and not Path(command[-1]).exists()


@pytest.mark.parametrize(
    "case",
    [
        "version",
        "bool_version",
        "unknown_field",
        "nested_field",
        "schema",
        "duplicate_key",
        "nan",
        "overflow",
        "unsafe_integer",
        "count",
        "status",
        "rate",
        "mean",
        "interval",
        "members",
        "identity",
        "pair",
        "unit",
        "policy",
        "hash",
        "missing_analysis",
        "exclusion",
    ],
)
def test_invalid_reports_fail_before_creating_html(
    report_cases: dict[str, Path], tmp_path: Path, case: str
) -> None:
    report = json.loads(report_cases["mixed" if case == "exclusion" else "base"].read_text())
    primary = report["contrasts"][0]["estimates"]["enacted"]
    if case == "version":
        report["version"] = 1
    elif case == "bool_version":
        report["version"] = True
    elif case == "unknown_field":
        report["surprise"] = "unsupported"
    elif case == "nested_field":
        report["sessions"][0]["analysis"]["outcomes"]["enacted"]["extra"] = 1
    elif case == "schema":
        report["sessions"][0]["analysis"]["pairs"][0]["episodes"] = "wrong"
    elif case == "nan":
        primary["difference"] = float("nan")
    elif case == "overflow":
        primary["difference"] = float("inf")
    elif case == "unsafe_integer":
        report["runs"][0]["seeds"][0] = 2**53
    elif case == "count":
        report["planned_sessions"] += 1
    elif case == "status":
        report["conditions"]["private"]["statuses"]["failed"] = 1
    elif case == "rate":
        report["conditions"]["private"]["stages"]["enacted"]["resolved_rate"] = 0.5
    elif case == "mean":
        primary["left_mean"] = primary["right_mean"] = 0.5
    elif case == "interval":
        primary["interval"] = {"lower": 0.5, "upper": -0.5}
    elif case == "members":
        primary["members"][0]["block_id"] = "unknown"
    elif case == "identity":
        report["sessions"][0]["channel"] = "private"
    elif case == "pair":
        report["sessions"][0]["analysis"]["pairs"][0]["pair"] = ["A", "C"]
    elif case == "unit":
        primary["units"] = "chips_per_session"
    elif case == "policy":
        report["policy"]["bootstrap"]["confidence"] = 0.5
    elif case == "hash":
        report["experiment_settings_sha256"] = "0" * 64
    elif case == "missing_analysis":
        report["sessions"][0]["analysis"] = None
    elif case == "exclusion":
        primary["exclusions"][0]["reasons"] = {"private": ["invented"]}
    payload = json.dumps(report)
    if case == "duplicate_key":
        payload = payload.replace('"version": 2', '"version": 2, "version": 2', 1)
    source = tmp_path / "report.json"
    source.write_text(payload)
    with pytest.raises(ValueError):
        write_report(source, tmp_path / "bad.html")
    assert not (tmp_path / "bad.html").exists()


def test_review_links_are_local_encoded_and_bound_to_source(
    report_cases: dict[str, Path], tmp_path: Path
) -> None:
    data = json.loads(report_cases["mixed"].read_text())
    analysis = next(s["analysis"] for s in data["sessions"] if s["analysis"] is not None)
    sid = analysis["source"]["session_id"]
    game = report_cases["manifest"].parent / "run" / "sessions" / sid / "session.jsonl"
    review = tmp_path / 'review # & "%.html'
    write_review_page(game, review)
    mapping = tmp_path / "links.json"
    mapping.write_text(json.dumps({sid: review.name}))
    parsed = PageParser()
    parsed.feed(
        render_report(report_cases["mixed"], review_pages_path=mapping, output_directory=tmp_path)
    )
    links = json.loads(parsed.payload)["review_pages"]
    assert links[sid] == "./review%20%23%20%26%20%22%25.html"
    with pytest.raises(ValueError, match="output directory"):
        render_report(report_cases["mixed"], review_pages_path=mapping)
    content = review.read_text()
    review.write_text(content.replace(analysis["source"]["sha256"], "0" * 64))
    with pytest.raises(ValueError, match="does not match"):
        render_report(report_cases["mixed"], review_pages_path=mapping, output_directory=tmp_path)
    mapping.write_text(json.dumps({"unknown": review.name}))
    with pytest.raises(ValueError, match="unknown session"):
        render_report(report_cases["mixed"], review_pages_path=mapping, output_directory=tmp_path)


def test_renderer_does_not_require_original_artifacts(
    report_cases: dict[str, Path], tmp_path: Path
) -> None:
    # Only a copied report is needed; no manifest or journal resolution takes place.
    report = json.loads(report_cases["base"].read_text())
    for run in report["selection"]["runs"]:
        run["directory"] = "/definitely-not-present/saved-run"
    isolated = tmp_path / "report.json"
    isolated.write_text(json.dumps(report))
    assert "Communication &amp; coordination" in render_report(isolated)
    assert read_comparison_report(isolated.read_text()) == report
