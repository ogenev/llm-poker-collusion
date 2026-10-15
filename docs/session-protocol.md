# Session protocol v1

This protocol extends the [game rules](game-protocol.md) to repeated hands with
communication and bounded player memory. These are configurable implementation
and pilot defaults. Freeze the research settings separately before evaluation.

## Configuration

`SessionConfig` validates these fields at construction:

| Field | Default | Rule |
| --- | --- | --- |
| `hands` | 30 | Positive integer; must equal the saved schedule length |
| `channel` | `Channel.NONE` | `NONE`, `PUBLIC`, or `PRIVATE` |
| `communication_rounds` | 2 | Positive integer; skipped entirely for `NONE` |
| `max_message_chars` | 500 | Positive integer, per message |
| `message_budget_chars` | 1000 | Nonnegative integer, per player per hand |
| `memory_hands` | 10 | Nonnegative integer, number of completed hands retained |
| `decision_timeout_seconds` | 30 | Finite positive number, per decision |

Unknown constructor fields and invalid values are rejected. Booleans are not
accepted as numeric configuration values. Every matched condition uses the
same deal schedule, identity rotation, hand count, and memory rule. Public and
private conditions use the same sending limits and number of rounds.

## Hand phases

Each session starts with empty player histories and zero cumulative rewards.
For each scheduled hand, the runner performs these phases:

1. **Deal.** Apply the explicit seat-indexed cards, rotate identities according
   to the saved schedule, and reset messages and each player's hand budget.
2. **Communication.** In enabled conditions, collect one optional-message
   decision from every player in every configured round. Deliver the round
   together after all decisions validate. No betting occurs in this phase.
3. **Betting.** Request one legal betting decision from the current actor,
   apply it through `PokerHand`, and repeat until the hand is terminal.
4. **Settlement.** Add each seat's net reward to its persistent identity.
5. **Memory update.** Construct each player's permitted completed-hand record
   and retain the most recent `memory_hands` records.

After the configured number of hands, the state becomes `COMPLETE`. There are
no between-hand messages, stack eliminations, adaptive stopping rules, or
additional decision calls during settlement. A completed-hand observation is
retained in memory and becomes available on that player's next decision.

## Communication and delivery

Every communication opportunity returns either `PassDecision()` or one
`MessageDecision(text, recipient)`:

- Public: `recipient=None`; deliver to all players, including the sender.
- Private: choose either other persistent identity, A, B, or C. Deliver only
  to the sender and selected recipient. Self-messages and unknown recipients
  are rejected. Recipient choices follow identities as seats rotate.
- No communication: make no communication decision calls and expose no sending
  options. Betting remains unchanged.

Messages must contain non-whitespace text. Preserve the exact text without
trimming, truncation, or normalization. Length is Python `len(text)`, measured
in Unicode code points, including spaces. Charge each accepted message once
against the sender's budget, including a public broadcast. The message must fit
both its per-message limit and the sender's remaining hand budget.

A pass consumes its round opportunity but no characters. With zero remaining
budget, continue requesting pass-only decisions for the remaining rounds.
Unused opportunities and characters do not carry over to another hand.
Public broadcasts have more recipients than private messages; sending
opportunities and characters are matched, not received-message volume.

Construct all three observations before invoking any round callback. Callbacks
run concurrently, and messages from the current round are absent from all
observations until every result validates. Within a delivered round, order
messages by sender identity A, B, C regardless of response timing. Round 2 can
respond to messages delivered in round 1. Passes, other players' budgets, and
the existence of private messages between other players are never exposed.
Messages contain no global sequence numbers, timestamps, or audit identifiers.

## Player views and memory

The async decision callable receives only an immutable `PlayerView`. It contains
the player's identity, seat mapping, current hand index and session length,
decision phase, the permitted `PokerView`, delivered messages, bounded history,
own cumulative settled reward, and current sending options and limits.

During communication, the nested poker view exposes no betting actor or legal
betting actions. During betting, only the actual actor is called. A betting
decision is `BetDecision(Action.CHECK/BET/CALL/FOLD)` and must be legal in the
current game state. Messages and passes cannot substitute for betting actions.
Return the protocol's exact decision classes and built-in strings for message
text/recipients; arbitrary subclasses are rejected so accepted decisions remain
serializable without loading callback code.

Each `HandMemory` records the hand index, seat mapping, terminal poker view,
and messages that this player sent or received. Card disclosure follows the
game protocol: other folded cards and an uncontested winner's card remain
hidden. A message claiming a card is not a verified card disclosure.

Keep the last N completed hand records in chronological order, without model
summaries. Remove older records as whole hands. `memory_hands=0` removes all
completed-hand records; the current hand and own cumulative reward remain
available. Cumulative rewards include all settled hands, including forgotten
ones. No other player's history, total reward, budget, pending messages, or
future cards enter the view.

All callbacks must use supplied memory and avoid retaining conversation state
outside the runner. The bundled passive and seeded-random policies are
stateless. The seeded policy derives a local RNG from its seed and public
decision coordinates, so it has no hidden mutable RNG cursor. These policies
test execution; they do not measure model competence or coalition formation.

## Failure and cancellation

The runner makes one attempt per decision and performs zero retries. Malformed
or wrong-phase decisions, illegal actions, invalid recipients, budget overruns,
callback exceptions, and timeouts terminate the session as `FAILED`. A refusal
must be surfaced as a failure or invalid decision; never replace it with a
pass, fold, or another model decision. Future provider transport retries must
be explicitly specified and recorded before live evaluation.

Validate the entire communication round before charging or delivering any of
its messages. If any player fails, preserve valid pending messages in trusted
state but deliver none from that round. Messages delivered in earlier rounds
remain intact. Report the primary failure in identity order when several
players fail in the same round. Do not continue betting or start another hand.

Return partial `SessionState` containing the failure's kind, source phase,
hand, round, and player, plus the current poker snapshot, completed-hand count,
settled rewards, budgets, and bounded histories. An unfinished hand contributes
no reward and no completed-hand memory. A failed session is not a shorter
successful session and must remain excluded from complete-session results or
handled by a separately predefined analysis rule.

Cancellation propagates as `SessionInterrupted`, an `asyncio.CancelledError`
subclass carrying the partial state with phase `INTERRUPTED`. Outstanding
round callbacks are cancelled and awaited. Callbacks must be cooperative
async functions; timeouts and cancellation cannot stop synchronous blocking
code or a callback that suppresses cancellation indefinitely.

## Recording and replay boundary

`SessionState` is trusted in-memory state, not a recovery checkpoint. It contains
all players' bounded histories and the full hidden schedule, and must never be
passed to a player. Pass an optional `JsonlRecorder` to retain the complete audit,
including forgotten hands, exact callback views and supported responses,
accepted decisions before effects, and failure/cancellation outcomes. Completed
responses in an interrupted round remain in the journal even when they have not
been assembled into `state.pending_messages`; unfinished callbacks have no
fabricated response. See the [recording protocol](recording-protocol.md).

Replay uses recorded responses through the same runner and verifies all events
and the terminal state without calling players. It returns completed, failed,
or cleanly interrupted state. Abrupt exits or persistence failures may leave only
an incomplete prefix, which can be inspected but not resumed or counted as a
complete session. Disk errors propagate rather than becoming agent failures.
Robust recovery and intervention branches remain Phase 2. Scripted demos remain
preparation data, not research evaluation data.
