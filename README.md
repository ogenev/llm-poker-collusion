# Private communication and coalition evidence in LLM poker

Does private communication make individually rewarded AI poker players more
likely to coordinate against another player? This repository contains the
experiment framework, protocols, and exploratory results for the
[Apart AI Collusion Research Sprint](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25),
23–25 October 2026.

Three persistent players play repeated, simplified poker with either no
communication, public messages, or private messages. Matched conditions use the
same cards and seat rotations. We inspect what players say, what they can know,
and what they subsequently do; winnings alone do not identify a coalition.

**[Read the paper](docs/poker-collusion-report.pdf) ·
[Reviewer guide](docs/reviewer-guide.md) ·
[Worked evidence examples](docs/evidence-examples.md) ·
[Offline demo](#try-the-offline-demo) ·
[Documentation index](docs/README.md)**

## What this project contributes

1. **A reusable experiment framework:** three communication conditions,
   individually rewarded players, matched cards, rotating seats, and replayable
   records of exactly what each player could see.
2. **Experiments with two models:** GPT-6.1 Sol and GPT-6 Luna, followed by Luna
   replication, duration comparisons, and tests of honesty wording.
3. **An audit connecting talk to action:** card claims checked against actual
   cards, replies checked against delivery timing, and promises checked against
   subsequent betting.

## Findings at a glance

Both models used private messaging more often in the initial neutral pilots
(paper, Figure 1):

| Model | Public messages | Private messages | Source |
| --- | ---: | ---: | --- |
| GPT-6.1 Sol | 0/216 (0.0%) | 198/216 (91.7%) | [Sol pilot](docs/neutral-pilot-iteration-report-2026-10-24.md#public-silence-and-frequent-private-messaging) |
| GPT-6 Luna | 98/216 (45.4%) | 155/216 (71.8%) | [Luna pilot](docs/luna-neutral-iteration-report-2026-10-24.md#neutral-results-and-evidence-checks) |

Each denominator is 3 players × 2 message rounds × 12 hands × 3 sessions.
These are communication opportunities, not independent trials or coalition
counts. Private use exceeded public use in each initial matched set for both models.

Some Luna exchanges implemented truthful information sharing. False claims,
broken promises, and an ambiguous fold of an unbeatable ace complicate the
interpretation. Honesty wording produced inconsistent changes across four saved
contexts. **The study does not establish lasting coalitions, a reliable
coalition-rate difference, or a causal profit advantage.** See the
[paper-to-evidence map](docs/reviewer-guide.md#paper-to-evidence-map) and
[worked examples](docs/evidence-examples.md) for the supporting and contrary cases.

## Research status

Sprint collection is complete; the results are exploratory. The framework and
smoke tests predate 23 October. Qualification, neutral pilots, and follow-up
studies ran during 23–25 October 2026. The final audit covers 85 supplied game
journals, including controls and failed attempts; this is an audit coverage
count, not 85 independent neutral replications.

Codex performed the detailed transcript audit. Ognyan Genev reviewed messages,
actions, findings and conclusions; the annotations retain their AI provenance.
The [final evidence review](docs/reviewer-audit-2026-10-26.md) explains coverage
and limitations. The [research log](docs/research-log.md) preserves chronology.
Historical plans and pending-review statements describe their dated checkpoints.

## Repository map

| Location | Contents |
| --- | --- |
| [`docs/`](docs/README.md) | Paper, reviewer guide, results, methods, and historical records |
| [`configs/`](configs) | Recorded experiment settings, model prices, and selection policies |
| [`src/poker_collusion/`](src/poker_collusion) | Game/session engine, model adapter, recording, analysis, and review tools |
| [`scripts/`](scripts) | Command-line entry points for offline review and experiment execution |
| [`tests/`](tests) | Offline tests of mechanics, privacy, delivery, recording, and analysis |
| `runs/` | Local raw evidence and generated outputs; **Git-ignored** |
| [Research overview](llm-poker-collusion-research-project.md) | Original research design and longer-term scope |
| [`TODO.md`](TODO.md) | Development history and broader roadmap, including work beyond this sprint |

Raw journals, transcripts, review exports, and evidence archives are separate
from Git. A clone does not include them. Relative `runs/` links in historical
reports work only when the corresponding evidence has been supplied. See the
[evidence availability notes](docs/reviewer-guide.md#evidence-availability).

## Try the offline demo

Use Python 3.13 and [uv](https://docs.astral.sh/uv/). `uv.lock` records dependency
versions. Run from the repository root:

```sh
uv sync --locked
POKER_DEMO_DIR="runs/preparation/reviewer-demo-001"
mkdir -p "$POKER_DEMO_DIR"
uv run --locked python scripts/demo_session.py --channel private --hands 3 --seed 0 --log "$POKER_DEMO_DIR/session.jsonl"
uv run --locked python scripts/replay_session.py "$POKER_DEMO_DIR/session.jsonl"
uv run --locked python scripts/generate_review_page.py "$POKER_DEMO_DIR/session.jsonl" --output "$POKER_DEMO_DIR/review.html"
```

Open `runs/preparation/reviewer-demo-001/review.html` in your browser. You should
see three hands with messages, cards, betting actions, and review controls.
Replay should report `"verified": true` and `"completed_hands": 3`.
Choose a new directory name when repeating the demo; existing files are protected.

This example uses scripted players and makes no model API calls. It demonstrates
recording and review, not empirical model behavior. Initial installation downloads
dependencies. The [offline review guide](docs/offline-review.md) explains the
viewer and adds a three-condition Inspect example; the
[complete walkthrough](docs/workflow-walkthrough.md) continues through annotation
and analysis.

## Setup and offline checks

After installing the locked environment above, check the framework with:

```sh
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
```

These checks use scripted models or simulated provider responses and require
no API credentials. Local event-loop sockets and writable XDG data/cache
directories are required. Optional browser tests have additional setup in the
[workflow walkthrough](docs/workflow-walkthrough.md#2-check-the-installation).

## How the experiment works

OpenSpiel supplies three-player Kuhn poker: one card each from J/Q/K/A, a
one-chip ante, at most one one-chip bet, and no raises. Our session engine
adds persistent identities, rotating seats, optional communication, and bounded
memory. Public messages reach everyone; private messages reach the sender and
one chosen recipient. All messages in a round are generated before delivery,
so only a later round can respond to an offer.

Each decision receives only that player's permitted view. Audit journals keep
the hidden deal, exact views, responses, actions, and outcomes for review and
offline replay. They are never supplied to the players.

- [Game rules](docs/game-protocol.md) and [session protocol](docs/session-protocol.md)
- [Model prompts and response format](docs/model-protocol.md)
- [Recording and replay](docs/recording-protocol.md)
- [Coalition rubric](docs/collusion-rubric.md) and [annotation format](docs/annotation-format.md)
- [Framework examples and historical checks](docs/framework-reference.md)
- [Complete offline workflow](docs/workflow-walkthrough.md)
