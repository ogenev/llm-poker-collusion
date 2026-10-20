# Workflow test, then human usability check

Run this walkthrough on your local machine, from your own repository checkout,
to exercise the current framework from saved gameplay to a report.
Complete this technical walkthrough first, then follow the
[human usability check](usability-check.md). The second part includes exporting
your own reviews and following them through analysis and reporting.

All gameplay here is scripted preparation data. Inspect runs its offline mock;
no provider credentials, paid model calls, or live experiments are needed.
Initial dependency installation may need network access. Passing this walkthrough
checks the plumbing, not model competence, human agreement, or research findings.

```text
Inspect mock → game/model journals + Inspect log → saved-run verification
                                                 ↓
source journal → browser review → annotation JSON → validation
                                                 ↓
                   single-session analysis → matched comparison → HTML report
```

The comparison command calls the single-session analyser itself. You do not
feed individual analysis JSON files into the comparison command.

## 1. Prepare your local checkout

Use Python 3.13, Git, and [uv](https://docs.astral.sh/uv/). The commands below use
Bash/Zsh syntax, suitable for a macOS or Linux terminal. For an existing checkout,
open a terminal in its root directory and update your local `main` branch:

```sh
git status --short --branch
git pull --ff-only origin main
```

Run the pull when the status shows `main` and a clean working tree. If you have
local work or are on another branch, preserve it and resolve that before updating.
If you do not yet have a checkout, instead run these commands from your preferred
projects directory:

```sh
git clone https://github.com/ogenev/llm-poker-collusion.git
cd llm-poker-collusion
```

All remaining commands start from that local repository root. There is no
`/workspace` path requirement and no cloud runtime to connect to. The guides and
code come from Git; previously generated cloud reports, examples, and results
notes do **not**, because `runs/` is ignored. The steps below create your own
artifacts locally.

Use the same terminal throughout both guides so the exported path persists.
Choose an unused suffix each time; do not delete an earlier check to rerun it.
Stop if a command fails and use the troubleshooting table below.

```sh
export POKER_CHECK_DIR="$PWD/runs/preparation/workflow-check-001"
mkdir -p runs/preparation
mkdir "$POKER_CHECK_DIR"
export XDG_CACHE_HOME="$POKER_CHECK_DIR/.cache"
export XDG_DATA_HOME="$POKER_CHECK_DIR/.local/share"
uv sync --locked
git rev-parse HEAD > "$POKER_CHECK_DIR/code-commit.txt"
```

The XDG paths give Inspect writable cache/data locations. Inspect also needs
local event-loop sockets even with an offline model. Generated artifacts stay
under Git-ignored `runs/`. Preserve journals, downloads, and revision predecessors.

If you reopen your terminal, restore the three exports above with the **same**
directory; skip `mkdir` and resume at the next unfinished step. New output files
are exclusive: choose a new filename when deliberately repeating a command.

## 2. Check the installation

For a fresh checkout or after code changes:

```sh
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
```

Expected: no failures. At the report-viewer implementation, the default suite
has **1,185 passing tests and two optional browser tests skipped**; with both
browser tests enabled, **1,187 pass**. Counts can grow with later changes. If the
same unchanged code has already passed these checks on your local installation,
proceed to step 3. A successful cloud run does not verify your local environment.

Optional browser automation needs Node/npm, Playwright, and Chromium. You can
skip this block and still perform the full manual usability check with your own
browser. To run automation, install its tools inside the ignored check directory
and let Playwright install its matching Chromium (these downloads need network):

```sh
npm install --prefix "$POKER_CHECK_DIR/browser-tools" playwright
node "$POKER_CHECK_DIR/browser-tools/node_modules/playwright/cli.js" install chromium
POKER_REVIEW_BROWSER=1 POKER_REPORT_BROWSER=1 \
NODE_PATH="$POKER_CHECK_DIR/browser-tools/node_modules" \
uv run --locked pytest -q tests/test_review_browser.py tests/test_report_browser.py
```

Leave `CHROMIUM_PATH` unset to use Playwright's installed browser; alternatively,
set it to an existing Chromium executable on your machine. There is no dependency
on a Linux-specific browser path. See [browser setup](review-form.md#development-checks)
for the test-only HTTP fixture mode if your browser policy blocks `file://`.
Browser automation is separate from the human check in part two.

## 3. Test rubric examples, replay, and single-session analysis

```sh
uv run --locked python scripts/generate_annotation_examples.py \
  "$POKER_CHECK_DIR/rubric"
uv run --locked python scripts/replay_session.py \
  "$POKER_CHECK_DIR/rubric/06-ambiguous-play.jsonl"
uv run --locked python scripts/validate_annotation.py \
  "$POKER_CHECK_DIR/rubric/06-ambiguous-play.annotation.json" \
  --log "$POKER_CHECK_DIR/rubric/06-ambiguous-play.jsonl"
uv run --locked python scripts/analyze_session.py \
  "$POKER_CHECK_DIR/rubric/06-ambiguous-play.jsonl" \
  --annotation "$POKER_CHECK_DIR/rubric/06-ambiguous-play.annotation.json" \
  --output "$POKER_CHECK_DIR/ambiguous-scripted.analysis.json"
uv run --locked python scripts/analyze_session.py \
  "$POKER_CHECK_DIR/rubric/06-ambiguous-play.jsonl" \
  --output "$POKER_CHECK_DIR/ambiguous-unreviewed.analysis.json"
```

Expected:

- Generation reports six examples, all replayed and validated. Each has a
  journal and an explicitly **scripted** annotation.
- Replay reports `verified: true`, status `complete`, and one completed hand.
- Validation reports `valid: true`, `reviewer_kind: scripted`, and scope
  `structure_and_evidence_links_only`.
- The selected scripted ambiguous review has `proposed: observed`,
  `accepted: uncertain`, and `enacted: uncertain` under `outcomes.*.verdict`.
- The unreviewed analysis has `review: null` and null stage verdicts, while
  replay and payoff facts remain available. Missing review is not a negative.

These six authored examples are **not matched comparison blocks**. Use them for
single-session and usability checks; do not put them in a comparison manifest.

## 4. Run and verify the matched Inspect example

```sh
uv run --locked python scripts/generate_comparison_example.py \
  "$POKER_CHECK_DIR/matched"
uv run --locked python scripts/verify_run.py "$POKER_CHECK_DIR/matched/run"
uv run --locked python scripts/compare_sessions.py \
  "$POKER_CHECK_DIR/matched/comparison.json" \
  --output "$POKER_CHECK_DIR/matched/report.json"
```

Expected: saved-run verification reports `passed: true`. Comparison reports
three planned blocks and nine planned sessions. Each block has the same saved
deals/seat rotations across `none`, `public`, and `private`; each session contains
three hands. The mock passes communication and checks/calls. Its supplied
annotations are complete scripted negatives.

Inspect executes and records the sessions. The comparison reuses saved evidence;
it neither calls a model nor judges coalition behavior.

## 5. Generate source review forms and their links

This copyable helper only builds empty review forms and file indexes. It assigns
no human judgments. It creates six rubric forms and nine matched-session forms,
with readable sample filenames such as `block-0-private.html`.

```sh
uv run --locked python - <<'PY'
import json
import os
from pathlib import Path
from poker_collusion.durable_jsonl import DurableJsonl
from poker_collusion.review_page import write_review_page

root = Path(os.environ["POKER_CHECK_DIR"])
for log in sorted((root / "rubric").glob("*.jsonl")):
    write_review_page(log, root / "forms" / "rubric" / f"{log.stem}.html")

report = json.loads((root / "matched" / "report.json").read_text())
links, index = {}, {}
for session in report["sessions"]:
    sample = session["sample_id"]
    identity = session["analysis"]["source"]["session_id"]
    log = root / "matched" / "run" / "sessions" / identity / "session.jsonl"
    page = root / "forms" / "matched" / f"{sample}.html"
    write_review_page(log, page)
    links[identity] = f"../forms/matched/{sample}.html"
    index[sample] = {"log": str(log.relative_to(root)),
                     "page": str(page.relative_to(root))}

with DurableJsonl(root / "matched" / "review-pages.json") as output:
    output.write(links)
with DurableJsonl(root / "session-index.json") as output:
    output.write(index)
(root / "human").mkdir()
print(f"Created 15 blank forms, 9 source links, and a session index in {root}")
PY
```

## 6. Render the complete comparison

```sh
uv run --locked python scripts/render_report.py \
  "$POKER_CHECK_DIR/matched/report.json" \
  --review-pages "$POKER_CHECK_DIR/matched/review-pages.json" \
  --output "$POKER_CHECK_DIR/matched/report.html"
```

Expected: `generated: true`. The renderer takes **report.json**, the saved
analysis, while `compare_sessions.py` takes **comparison.json**, the selection
manifest. The renderer validates saved data and source-page links; it does not
replay journals or rerun statistics.

Open `$POKER_CHECK_DIR/matched/report.html` in your local browser using its
**Open File** command, or locate it under
`runs/preparation/workflow-check-001/matched/` in Finder/your file manager and
double-click it. Substitute your suffix if different. No web server is needed.
It should show
preparation/mock data, nine audited complete sessions, nine selected reviews,
three eligible primary blocks, both enacted rates 0%, and a difference of 0 pp.
The zero-width interval must have a warning; it does not establish certainty.
Defer the detailed reading tasks to the human usability check.

## 7. Check that omitted reviews remain visible

Create two separate manifests without modifying the original. The first omits
one selected review; the second selects no reviews. No journal or review file
is deleted, and no scientific label is changed.

```sh
uv run --locked python - <<'PY'
import copy
import json
import os
from pathlib import Path
from poker_collusion.durable_jsonl import DurableJsonl

base = Path(os.environ["POKER_CHECK_DIR"]) / "matched"
original = json.loads((base / "comparison.json").read_text())
partial = copy.deepcopy(original)
partial["runs"][0]["reviews"] = [
    row for row in partial["runs"][0]["reviews"]
    if row["sample_id"] != "block-0-private"
]
unreviewed = copy.deepcopy(original)
unreviewed["reviewer_kind"] = "human"
unreviewed["runs"][0]["reviews"] = []
for name, manifest in [("partial", partial), ("unreviewed", unreviewed)]:
    with DurableJsonl(base / f"comparison-{name}.json") as output:
        output.write(manifest)
PY
```

Generate the reports:

```sh
uv run --locked python scripts/compare_sessions.py \
  "$POKER_CHECK_DIR/matched/comparison-partial.json" \
  --output "$POKER_CHECK_DIR/matched/report-partial.json"
uv run --locked python scripts/render_report.py \
  "$POKER_CHECK_DIR/matched/report-partial.json" \
  --review-pages "$POKER_CHECK_DIR/matched/review-pages.json" \
  --output "$POKER_CHECK_DIR/matched/report-partial.html"
uv run --locked python scripts/compare_sessions.py \
  "$POKER_CHECK_DIR/matched/comparison-unreviewed.json" \
  --output "$POKER_CHECK_DIR/matched/report-unreviewed.json"
uv run --locked python scripts/render_report.py \
  "$POKER_CHECK_DIR/matched/report-unreviewed.json" \
  --review-pages "$POKER_CHECK_DIR/matched/review-pages.json" \
  --output "$POKER_CHECK_DIR/matched/report-unreviewed.html"
```

Expected saved results:

| Report | Planned sessions | Selected reviews | Primary eligible blocks | Primary difference |
| --- | --- | --- | --- | --- |
| `report.html` | 9 | 9 | 3 / 3 | 0 pp |
| `report-partial.html` | 9 | 8 | 2 / 3 | 0 pp |
| `report-unreviewed.html` | 9 | 0 | 0 / 3 | Unavailable, not zero |

In all three, the private/public **payoff** comparison still has three eligible
blocks: all game/model evidence is complete. Missing labels exclude stage
estimates without discarding valid payoff facts. The unreviewed manifest's
`reviewer_kind: human` selects the kind to use; it creates no human reviews.

## 8. Record the technical result and start the human check

Create a note in `$POKER_CHECK_DIR/check-results.md` with the saved commit,
OS/browser, date, commands that failed, expected-versus-actual observations, and
artifact paths. Record technical checks and human tasks separately as
**passed**, **failed**, or **not run**. Do not mark human work complete because
an automated test passed.

Continue with [Human usability check](usability-check.md). Keep this directory
and its layout: source links are relative, and revision validation needs the
original downloaded bytes.

## Troubleshooting

| Symptom | Next action |
| --- | --- |
| Output already exists | Resume at the unfinished step, or choose a new directory/output name. Writers deliberately refuse overwrites. |
| Cache/data permission error | Restore the writable XDG exports from step 1. |
| Inspect local socket denied | Use an environment that permits local sockets; this does not require live provider access. |
| Optional browser tests skipped | Set their opt-in variables and install browser tools if you want those checks. |
| Browser blocks local HTML | Open the locally generated file in a browser permitted to read local HTML. Preserve the artifact tree's relative paths. This is a browser-policy limitation. |
| Review-page link rejected | Use the form generated from that exact journal; session ID, SHA-256, and status must match. |
| Comparison or replay fails | Preserve the error and inputs. Check the correct manifest and source files; do not edit logs/hashes to make a check pass. |

Live provider compatibility is a separate, explicitly bounded
[live smoke procedure](live-smoke.md). The competence/control pilot, rubric
calibration, evaluation freeze, and research runs remain separate sprint work.
