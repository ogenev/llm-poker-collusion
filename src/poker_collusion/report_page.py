"""Generate a self-contained comparison viewer from a saved JSON snapshot."""

import hashlib
import json
import os
import re
from html.parser import HTMLParser
from importlib.resources import files
from pathlib import Path
from urllib.parse import quote

from poker_collusion.model_adapter import _read_object
from poker_collusion.report_validation import read_comparison_report, require


class _ReviewSource(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.active = False
        self.count = 0
        self.payload = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and dict(attrs).get("id") == "review-data":
            self.count += 1
            self.active = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.active = False

    def handle_data(self, data: str) -> None:
        if self.active:
            self.payload += data


def _review_links(
    mapping_path: Path, output_directory: Path, sources: dict[str, object]
) -> dict[str, str]:
    mapping = _read_object(mapping_path.read_text(encoding="utf-8"))
    links = {}
    for session_id, target in mapping.items():
        require(session_id in sources, "review-page link names an unknown session")
        require(isinstance(target, str) and bool(target), "review-page path must be a string")
        assert isinstance(target, str)
        page = (mapping_path.parent / target).resolve()
        require(page.suffix.lower() == ".html", "review-page links require a local HTML file")
        parser = _ReviewSource()
        parser.feed(page.read_text(encoding="utf-8"))
        require(parser.count == 1, "review-page source metadata is missing or ambiguous")
        require(
            _read_object(parser.payload).get("source") == sources[session_id],
            "review-page source does not match the analysed journal",
        )
        # A relative URL beginning './' cannot become a URL scheme, even for unusual names.
        relative = os.path.relpath(page, output_directory.resolve())
        links[session_id] = "./" + quote(relative, safe="/")
    return links


def render_report(
    report_path: str | Path,
    *,
    review_pages_path: str | Path | None = None,
    output_directory: str | Path | None = None,
) -> str:
    raw = Path(report_path).read_bytes()
    report = read_comparison_report(raw.decode("utf-8"))
    links = {}
    if review_pages_path is not None:
        if output_directory is None:
            raise ValueError("Review-page links require an output directory")
        sources = {
            row["analysis"]["source"]["session_id"]: row["analysis"]["source"]
            for row in report["sessions"]
            if row["analysis"] is not None
        }
        links = _review_links(Path(review_pages_path), Path(output_directory), sources)
    payload = json.dumps(
        {"report": report, "report_sha256": hashlib.sha256(raw).hexdigest(), "review_pages": links},
        ensure_ascii=True,
        allow_nan=False,
    )
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    assets = files("poker_collusion").joinpath("report_assets")
    scripts = "\n".join(
        assets.joinpath(name).read_text(encoding="utf-8")
        for name in ("base.js", "overview.js", "sessions.js")
    )
    replacements = {
        "NONCE": hashlib.sha256(payload.encode()).hexdigest(),
        "PAYLOAD": payload,
        "STYLE": assets.joinpath("report.css").read_text(encoding="utf-8"),
        "SCRIPT": '"use strict";\n(() => {\n' + scripts + "\n})();",
    }
    template = assets.joinpath("report.html").read_text(encoding="utf-8")
    return re.sub(
        r"@@(NONCE|PAYLOAD|STYLE|SCRIPT)@@", lambda match: replacements[match[1]], template
    )


def write_report(
    report_path: str | Path,
    output_path: str | Path,
    *,
    review_pages_path: str | Path | None = None,
) -> None:
    path = Path(output_path)
    html = render_report(
        report_path, review_pages_path=review_pages_path, output_directory=path.parent
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
        output.write(html)
        output.flush()
        os.fsync(output.fileno())
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
