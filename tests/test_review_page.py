import asyncio
import hashlib
import json
import stat
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest

from poker_collusion.annotation_examples import generate_examples
from poker_collusion.review_page import render_review_page, write_review_page


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.payload = ""
        self.scripts = 0
        self.external: list[str] = []
        self.in_payload = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "script":
            self.scripts += 1
            self.in_payload = attributes.get("id") == "review-data"
        for key in ("src", "href"):
            if attributes.get(key):
                self.external.append(str(attributes[key]))

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.in_payload = False

    def handle_data(self, data: str) -> None:
        if self.in_payload:
            self.payload += data


@pytest.fixture(scope="module")
def examples(tmp_path_factory: pytest.TempPathFactory) -> tuple[tuple[Path, Path], ...]:
    return asyncio.run(generate_examples(tmp_path_factory.mktemp("review-pages") / "examples"))


@pytest.mark.parametrize("index", range(6))
def test_page_embeds_exact_source_without_labels(
    examples: tuple[tuple[Path, Path], ...], index: int
) -> None:
    log, annotation = examples[index]
    original = (log.read_bytes(), annotation.read_bytes())
    page = render_review_page(log)
    parsed = PageParser()
    parsed.feed(page)
    payload = json.loads(parsed.payload)
    assert parsed.scripts == 2
    assert parsed.external == []
    assert payload["source"]["sha256"] == hashlib.sha256(original[0]).hexdigest()
    assert payload["source"]["status"] == "complete"
    assert payload["rubric"] == {"id": "coalition", "version": "0.1"}
    assert "reviewer" not in payload and "pair_reviews" not in payload
    source_events = [json.loads(line) for line in original[0].splitlines()]
    assert payload["events"] == [
        {key: event[key] for key in ("sequence", "event", "data")} for event in source_events
    ]
    assert "connect-src 'none'" in page
    assert (log.read_bytes(), annotation.read_bytes()) == original


def test_untrusted_transcript_cannot_close_script_or_replace_template(
    examples: tuple[tuple[Path, Path], ...], tmp_path: Path
) -> None:
    events: list[dict[str, Any]] = [
        json.loads(line) for line in examples[3][0].read_text().splitlines()
    ]
    attack = "</script><script>globalThis.injected=true</script><img src=x>@@SCRIPT@@ & \u2028"
    for event in events:
        if event["event"] == "messages_delivered":
            event["data"]["messages"][0]["text"] = attack
            break
    source = tmp_path / "hostile.jsonl"
    source.write_text("".join(json.dumps(event) + "\n" for event in events))
    page = render_review_page(source)
    parsed = PageParser()
    parsed.feed(page)
    assert parsed.scripts == 2 and not parsed.external
    assert attack not in page
    payload = json.loads(parsed.payload)
    messages = next(e for e in payload["events"] if e["event"] == "messages_delivered")
    assert messages["data"]["messages"][0]["text"] == attack


def test_exclusive_private_output_and_source_preservation(
    examples: tuple[tuple[Path, Path], ...], tmp_path: Path
) -> None:
    source = examples[0][0]
    output = tmp_path / "new" / "review.html"
    write_review_page(source, output)
    original = output.read_bytes()
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    with pytest.raises(FileExistsError):
        write_review_page(source, output)
    assert output.read_bytes() == original
    with pytest.raises(FileExistsError):
        write_review_page(source, source)


def test_incomplete_source_and_torn_tail_are_preserved(
    examples: tuple[tuple[Path, Path], ...], tmp_path: Path
) -> None:
    source = tmp_path / "incomplete.jsonl"
    source.write_bytes(b"\n".join(examples[0][0].read_bytes().splitlines()[:5]) + b'\n{"torn":')
    parsed = PageParser()
    parsed.feed(render_review_page(source))
    payload = json.loads(parsed.payload)
    assert payload["source"]["status"] == "incomplete"
    assert payload["source"]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert payload["trailing_bytes"] > 0
    assert len(payload["events"]) == 5


def test_generator_cli_errors_and_does_not_overwrite(
    examples: tuple[tuple[Path, Path], ...], tmp_path: Path
) -> None:
    output = tmp_path / "review.html"
    command = [
        sys.executable,
        "scripts/generate_review_page.py",
        str(examples[0][0]),
        "--output",
        str(output),
    ]
    success = subprocess.run(command, capture_output=True, text=True, check=False)
    assert success.returncode == 0
    assert json.loads(success.stdout)["offline"] is True
    exists = subprocess.run(command, capture_output=True, text=True, check=False)
    assert exists.returncode == 2
    assert json.loads(exists.stdout)["generated"] is False
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    command[2] = str(empty)
    failed = subprocess.run(command, capture_output=True, text=True, check=False)
    assert failed.returncode == 2
    assert "empty" in json.loads(failed.stdout)["error"].lower()
