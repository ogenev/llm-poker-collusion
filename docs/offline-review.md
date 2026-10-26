# Inspect a game offline

The [README demo](../README.md#try-the-offline-demo) creates a three-hand private
session, replays it, and generates `review.html`. It uses scripted players and
requires no model credentials. Run those commands first; this guide explains
what to look for and how to inspect a matched run or a real experiment.

## Read the generated transcript

Open `runs/preparation/reviewer-demo-001/review.html` in a browser. The page
embeds its source journal and works offline.

1. Select **Hand 1** in the hand filter.
2. Read the delivered messages, including senders, recipients, and round numbers.
   A second-round response can use first-round messages; messages generated in
   the same round cannot respond to each other.
3. Follow the betting actions to the outcome. Expand the audit details to inspect
   the true deal; player views show only what that player was allowed to know.
4. Enable **Show all journal events** to inspect the exact decision requests and
   responses. The full audit contains more information than any player received.

The page also contains review controls for A-B, A-C, and B-C. You can inspect the
transcript without completing an annotation. To save an assessment, use the
[review form guide](review-form.md) and [coalition rubric](collusion-rubric.md).
Scripted messages are demonstration data, not observations about an LLM.

Expected command results:

| Command | Successful result |
| --- | --- |
| `demo_session.py` | `"status": "complete"`, `"completed_hands": 3`, and a new `session.jsonl` |
| `replay_session.py` | `"verified": true`, `"completed_hands": 3` |
| `generate_review_page.py` | `"generated": true`, `"offline": true`, and a new `review.html` |

## Verify a matched three-condition run

This optional example exercises the Inspect integration as well as the game
engine. After [installation](../README.md#try-the-offline-demo), run from the
repository root with a fresh output name:

```sh
POKER_MATCHED_DIR="runs/preparation/reviewer-matched-001"
uv run --locked python scripts/run_experiment.py configs/inspect-offline.json --offline --output "$POKER_MATCHED_DIR"
uv run --locked python scripts/verify_run.py "$POKER_MATCHED_DIR"
for journal in "$POKER_MATCHED_DIR"/sessions/*/session.jsonl; do
  uv run --locked python scripts/generate_review_page.py "$journal" --output "${journal%/session.jsonl}/review.html"
done
```

Expect three complete sessions, each with three hands: no communication, public,
and private. The verifier checks the run manifest, Inspect evaluation log,
session/model journals, usage accounting, and matched schedules, then replays
the sessions. Open a generated `review.html` in each session directory to compare
the communication conditions. The model is an offline mock and its usage is
synthetic; this is a software demonstration.

## Review a real experiment

The full empirical journals are distributed separately; see
[evidence availability](reviewer-guide.md#evidence-availability). The
[worked examples](evidence-examples.md#source-records-and-verification) give
session IDs, source paths, event numbers, and source hashes for three real hands.

Verify the supplied archive's checksum and per-file manifest, then follow its
reproduction instructions in a fresh extraction directory. Use its recorded
source version where required. Replace the placeholders below with actual paths:

```sh
uv run --locked python scripts/replay_session.py PATH_TO_SESSION_JSONL
uv run --locked python scripts/generate_review_page.py PATH_TO_SESSION_JSONL --output runs/reviewer-real-session.html
```

Open the generated HTML and select the cited hand. Read the preceding history
and contrary cases before assigning a coalition label. Replay verifies recorded
execution; it does not validate a scientific interpretation.

## If a command fails

| Symptom | Next step |
| --- | --- |
| Output already exists | Pick a fresh directory or filename. Existing journals and reviews are never overwritten. |
| A report's `runs/` link is missing | Obtain the named archive and follow its layout instructions. Those files are not part of a clone. |
| Dependency installation fails | Check Python 3.13 and network access, then retry `uv sync --locked`. |
| A sandbox blocks local sockets or cache writes | Run from a local terminal with writable XDG data/cache directories; see [workflow troubleshooting](workflow-walkthrough.md#troubleshooting). |
| A journal is incomplete | Use `replay_session.py PATH_TO_SESSION_JSONL --inspect` to inspect its committed prefix. Do not treat it as a completed session. |

For annotation validation, matched analysis, and report generation, continue
with the [complete workflow](workflow-walkthrough.md).
