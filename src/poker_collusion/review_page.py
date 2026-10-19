"""Build a standalone, offline human-review page from a stable saved journal."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict
from importlib.resources import files
from pathlib import Path

from poker_collusion.annotation_validation import source_for_log
from poker_collusion.annotations import RUBRIC_ID, RUBRIC_VERSION

_SCRIPTS = ("json.js", "validation.js", "state.js", "transcript.js", "form.js", "io.js")


def render_review_page(log_path: str | Path) -> str:
    """Embed source evidence, never example judgments, with no external assets."""
    source, log = source_for_log(log_path)
    payload = (
        json.dumps(
            {
                "source": asdict(source),
                "rubric": {"id": RUBRIC_ID, "version": RUBRIC_VERSION},
                "events": [asdict(event) for event in log.events],
                "trailing_bytes": log.trailing_bytes,
            },
            ensure_ascii=True,
            allow_nan=False,
        )
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    assets = files("poker_collusion").joinpath("review_assets")
    script = "\n".join(assets.joinpath(name).read_text(encoding="utf-8") for name in _SCRIPTS)
    # One nonce permits only the bundled scripts/styles. Transcript text is always
    # rendered as text, and the CSP prevents network requests from this local page.
    nonce = hashlib.sha256(payload.encode()).hexdigest()
    replacements = {
        "NONCE": nonce,
        "STYLE": assets.joinpath("review.css").read_text(encoding="utf-8"),
        "PAYLOAD": payload,
        "SCRIPT": '"use strict";\n(() => {\n' + script + "\n})();",
    }
    template = assets.joinpath("review.html").read_text(encoding="utf-8")
    # Replace template tokens in one pass, so source text resembling a token is inert.
    return re.sub(r"@@(NONCE|STYLE|PAYLOAD|SCRIPT)@@", lambda m: replacements[m[1]], template)


def write_review_page(log_path: str | Path, output_path: str | Path) -> None:
    """Create a private HTML file exclusively; never replace a source or review."""
    html = render_review_page(log_path)
    path = Path(output_path)
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
