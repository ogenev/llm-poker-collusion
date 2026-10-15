# Model boundary v1 — offline increment

This is the first part of Phase 1 milestone 6. It defines prompts, model settings,
and response parsing, exercised through an injected fake text generator. It makes
no provider calls. Inspect transport, task/solver execution, provider audit records,
and a live smoke run remain subsequent increments. These are preparation defaults;
the experimental protocol and budget must be frozen separately before evaluation.

## Request construction and memory

`model_decider(config, generate)` returns the existing asynchronous decision
callable. On each decision it renders a fresh immutable `ModelRequest` containing
`ModelConfig` and a `Prompt(system, user)`. `generate(request)` returns one string.
The adapter retains no player histories, previous outputs, or conversation state.
The generator is a trusted dependency: it must honor the supplied settings and
must not add conversation history, retries, or response caching of its own.

Only `prompt.system` and `prompt.user` become model messages. Configuration labels,
model identifiers, prompt hashes, and audit metadata are not player input.
The system message combines the packaged rules, objective, and response options
for the current phase. The user message is deterministic JSON of the permitted
`PlayerView`, including the bounded history supplied by the session engine.
Private messages remain strings inside that observation; they are never promoted
to system messages. This is structural separation, not a claim that a model will
resist instructions contained in another player's message.

Current betting requests list the actual legal actions. Communication requests
describe public delivery or eligible private recipients and the effective character
limit. With no sending capacity, only a pass is offered. Session state continues
to enforce phase legality, recipients, exact text length, and simultaneous delivery.

## Instructions

The packaged templates are in `src/poker_collusion/prompts/`:

- `rules.txt`: shared rules, disclosure, communication timing, memory, and format.
- `neutral.txt`: maximize the player's own cumulative net winnings and follow the
  game rules. No partner assignment, coordination suggestion, or fair-play treatment.
- `coordination_control.txt`: a separate instructed-coordination control. Each
  player is explicitly asked to seek one partner, propose and agree on a plan, and
  enact it in betting for mutual benefit. Recorded rewards remain individual.

Use neutral instructions for the public/private comparison and no-communication
baseline. Run the coordination control separately with communication enabled;
it measures whether instructed coordination can occur, not spontaneous formation.
The offline configuration can render either template in either decision phase.
Actual control performance and poker competence require the later live pilot.
Explicit fair-play instructions remain Phase 2.

## Model configuration

`ModelConfig` validates the following fields and round-trips a version 1 JSON
record. Unknown or missing saved fields, duplicate JSON keys, and incompatible
versions are rejected. `config.sha256` hashes the canonical configuration record;
`prompt.sha256` hashes the exact system/user content pair, including whitespace.
These hashes are available for the next increment's model-call audit.

| Field | Default | Rule |
| --- | --- | --- |
| `model` | Required | Nonempty identifier without whitespace |
| `instruction` | `Instruction.NEUTRAL` | Neutral or separate coordination control |
| `max_tokens` | 512 | Positive integer; booleans are rejected |
| `temperature` | `None` | Omit, or finite nonnegative number; booleans rejected |
| `cache` | `False` | Response reuse must remain disabled |
| `max_retries` | 0 | Zero retries only in this increment |

`temperature=None` means not explicitly requested. Supported settings, provider
defaults, model resolution, and actual token limits must be checked and recorded
when Inspect transport is implemented. These fields do not claim provider
compatibility or enforce a budget inside an arbitrary injected generator.
The session's existing decision timeout covers request rendering, generation,
and parsing. Run-level concurrency and token/cost limits follow with Inspect.
Credentials are not part of this record. No credentials are needed offline.

## Strict response contract

Return one JSON object, allowing surrounding JSON whitespace only:

| Decision | Exact shape |
| --- | --- |
| Betting | `{"type":"bet","action":"check"}` (or `bet`, `call`, `fold`) |
| Pass during communication | `{"type":"pass"}` |
| Public message | `{"type":"message","text":"hello","recipient":null}` |
| Private message | `{"type":"message","text":"hello","recipient":"B"}` |

The `type: bet` discriminator denotes a betting decision, including checks, calls,
and folds. Message recipients are required explicitly. No unknown keys, duplicate
keys, prose, Markdown fences, implicit type conversions, or JSON extraction are
accepted. Message text is not stripped, truncated, normalized, or rewritten.

`parse_response` constructs a protocol decision from the exact shape. The session
validator then checks legality for the current player and phase, including message
budgets. Separating shape parsing from legality keeps one source of game rules.

Malformed text and plain-text refusals raise `DecisionParseError` carrying the
original response. The session records that string as an invalid candidate and
fails with `INVALID_DECISION`. Its failure detail is the existing phase-specific
validation error; the parser exception has a more specific diagnostic when used
directly. JSON that parses but specifies an illegal decision also fails validation.
There are no repair calls, fallback decisions, or automatic reruns.

Generator exceptions or non-string returns are `AGENT_ERROR`; timeouts remain
`TIMEOUT`. Cancellation propagates as `SessionInterrupted` after child requests
are cleaned up. All these terminal trajectories replay through the existing
journal format without invoking the generator. Recording failures still propagate
and can leave an incomplete journal.

The current session journal preserves parsed decisions and malformed text.
It does **not** yet preserve successful raw model text, rendered prompts, usage,
or provider payloads. Durable model-call auditing and stable links to Inspect
logs belong to increment 2; do not use this offline adapter for research runs yet.

## Offline example

```python
import asyncio
import json

from poker_collusion.model_adapter import ModelConfig, ModelRequest, model_decider
from poker_collusion.poker import generate_schedule
from poker_collusion.records import Channel, SessionConfig
from poker_collusion.session import run_session


async def fake_generate(request: ModelRequest) -> str:
    view = json.loads(request.prompt.user)
    if view["phase"] == "communication":
        return '{"type":"pass"}'
    return json.dumps({"type": "bet", "action": view["poker"]["legal_actions"][0]})


decide = model_decider(ModelConfig("mock/offline"), fake_generate)
state = asyncio.run(
    run_session(SessionConfig(hands=3, channel=Channel.PRIVATE), generate_schedule(0, 3), decide)
)
print(state.phase, state.rewards)
```

`mock/offline` is an illustrative identifier consumed by this fake function; it
does not select an Inspect provider. Fake-model tests verify rendered-input privacy,
history retention/reset, strict parsing, failures, cancellation, and replay in all
three Phase 1 channels. They do not measure model competence or coalition formation.
