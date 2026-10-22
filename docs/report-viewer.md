# Standalone comparison report

The HTML viewer turns a saved [comparison analysis](comparison-protocol.md) into
an offline report with an overview, primary comparison chart, coverage tables,
secondary results, and a searchable session explorer. It uses the existing
Python package and a small amount of bundled JavaScript. Readers need only a
browser; there is no server, external asset, provider call, or model judge.

## Generate and open

After running the comparison command:

```sh
uv run --locked python scripts/render_report.py \
  runs/preparation/comparison-example-001/report.json \
  --output runs/preparation/comparison-example-001/report.html
```

The input is the **analysis JSON produced by `compare_sessions.py`**, not its
run-selection manifest. See the comparison protocol for commands that generate
the complete scripted example. Open the resulting HTML file in a browser.
If an output already exists, choose a new filename; the command never overwrites
it. Output is private (mode `0600`). Exit code 0 means it was generated; malformed
input, an invalid optional link, or an existing output returns code 2.

The report embeds all saved results, so the original run directories are not
needed for viewing. Generation does not replay journals, rerun the bootstrap,
revise annotations, or change inclusion decisions. The comparison JSON's exact
SHA-256 appears under provenance. The page includes the saved analysis code
hash, runtime, settings, original input references, and limitations.

## Reading the report

- **Overview:** dataset role, gameplay kind, model, instructions, settings,
  planned blocks/sessions, audited completion, and selected-review counts.
  Preparation and pilot data remain visibly identified.
- **Primary comparison:** saved private-minus-public enacted-coordination
  difference, both rates on the shared paired denominator, eligible/excluded
  blocks, and the configured uncertainty interval. `pp` means percentage points.
  The chart shows the saved point estimate and interval; the same values are
  also available as text. Unavailable estimates are never drawn as zero.
- **Completion and review coverage:** raw observed/not-observed/uncertain/unknown
  counts, completion statuses, and the resolved rate's own denominator. These
  condition rates can use different samples from the paired primary estimate.
- **Other results:** separate stages, no-communication baseline contrasts, and
  whole-session payoffs for fixed players and pairs. Expand a result to inspect
  its block membership, exclusions, and caveats.
- **Session explorer:** search IDs, reviewer text, or evidence; filter by channel,
  session status, review status, or exclusion reason. Results are paginated in
  groups of 25. Filters affect only the session list—every saved estimate and
  denominator remains fixed. A complete-session payoff can be eligible while
  the same session's coalition labels are excluded.
- **Session details:** reviewer/rubric/revision identifiers, source hashes,
  failures, metric-specific exclusion reasons, stage rollups, pair payoffs,
  episode explanations, alternatives, supporting and contradicting citations,
  and the full saved session analysis. Evidence references identify journal
  events; the original transcript is not embedded in the comparison JSON.

Use **Print report** for the visible report sections and any expanded details.
The filtered session table and its controls are omitted from printing; opening
a session's detail panel includes those details. The HTML remains the complete
interactive artifact. On narrow screens, wide tables scroll within their panels.

## Optional links to source review pages

Generate source pages using the existing review-form command:

```sh
uv run --locked python scripts/generate_review_page.py SESSION.jsonl \
  --output reviews/SESSION_ID.html
```

Create a JSON mapping of actual session IDs to existing local HTML files:

```json
{
  "SESSION_ID": "reviews/SESSION_ID.html"
}
```

Paths are relative to the mapping file (absolute local paths also work). Supply
it when rendering:

```sh
uv run --locked python scripts/render_report.py report.json \
  --review-pages review-pages.json --output report.html
```

The renderer checks each page's embedded session ID, journal hash, and status
against the selected session analysis. Unknown sessions, mismatched sources,
missing files, and ambiguous source metadata are errors. Links are encoded and
made relative to the output HTML. No remote URLs or automatic file discovery are
used. Keep linked pages in the same relative locations when moving the report.
The main report still works independently when no links are supplied.

**Open source review page** opens the transcript and review form. It does not
preload the selected annotation or assert that a human reviewed the session.
For a human annotation, import the selected JSON into that form to inspect it;
the existing form continues to reject scripted/model annotations as human work.

## Validation and limits

The renderer accepts `session_comparison_analysis` schema v2 and policy v0.1.
It rejects unknown fields/versions, duplicate JSON keys, invalid nested types,
non-finite numbers, inconsistent identities, block partitions, counts, units,
and summary/member arithmetic. Integers outside JavaScript's exact range
(±9,007,199,254,740,991) are rejected rather than rounded. Saved intervals are
checked for shape/range/availability, but are not recomputed.

These checks do not authenticate the report or establish the correctness of its
scientific labels. To verify original journals and selected annotations again,
rerun the comparison analyser. The viewer retains missingness and small-sample
limitations, including zero-width bootstrap warnings. It supplies no new
significance tests, causal-effect claims, exact formation timing, or judgments.

Text from reports and annotations is escaped when embedded and rendered as text
in the browser. A Content Security Policy allows only bundled scripts/styles and
blocks network requests. The page has no uploads, autosave, or editing controls.
Large datasets can still produce large files because all analysis data is
embedded, even though the session list is paginated.

Python API: `render_report(path)` returns HTML; `write_report(path, output_path)`
creates a new durable file. Both accept `review_pages_path=...`; direct rendering
with links also requires `output_directory=...` so relative URLs are correct.

## Development checks

Python tests cover schema and consistency errors, faithful data embedding,
exclusive output, CLI errors, hostile text, and source-bound review links.
The optional browser test checks filters with unchanged estimates, uncertainty,
evidence details, navigation, missing/failed sessions, pagination, mobile layout,
and print behavior. It rejects unexpected requests. These scripted checks do
not replace the planned human usability check.

With Node, Playwright, and Chromium installed separately:

```sh
POKER_REPORT_BROWSER=1 CHROMIUM_PATH=/usr/bin/chromium \
NODE_PATH=/path/to/node_modules \
uv run --locked pytest -q tests/test_report_page.py tests/test_report_browser.py
```

In managed browsers that prohibit `file://`, set
`POKER_REVIEW_BROWSER_HTTP=1`, as for the review-form tests. Playwright fulfills
the exact generated files at localhost without a running server. This checks
the UI; it does not change browser policy about local-file navigation.
