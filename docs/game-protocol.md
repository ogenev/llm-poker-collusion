# Game protocol v1

This specifies the game boundary. The [session protocol](session-protocol.md)
defines communication budgets, memory, and runtime failure handling. The
[model boundary](model-protocol.md) defines prompts and response parsing;
[Inspect execution](inspect-protocol.md) is implemented, with live provider
qualification pending in [the checklist](../TODO.md). This is
pre-sprint implementation work, not a frozen experimental protocol.

## Rules and settlement

Three seats, numbered 0, 1, and 2 in acting order, receive one card each without
replacement from J < Q < K < A. Internal card codes are 0, 1, 2, and 3. The fourth
card stays undealt and hidden. Every new hand uses the full deck, independently
of previous hands.

Each seat antes one chip. Seat 0 acts first. Before a bet, a player can check
(add nothing) or bet one additional chip. If all three check, the hand ends in
showdown. There is at most one opening bet and no raises.

After the opening bet, each other seat responds exactly once, in cyclic order:
call (add one chip) or fold (leave the hand, losing its ante). Seats that checked
earlier must also respond. The bettor does not act again. For example, if seat 2
bets after two checks, seats 0 and 1 must respond in that order. The hand ends
after both responses, or equivalently when only the bettor remains active.

With two or three active seats at the end, the highest active card wins. With
one active seat, that player wins without showing a card. Ranks are unique, so
there are no ties or split pots. The winner receives the entire pot. Net reward
equals chips received minus chips contributed; other players lose their own
contributions. Rewards sum to zero. Antes and one-chip bets are available on
every hand regardless of cumulative losses: there are no stacks, elimination,
side pots, pooled objectives, or transfers.

Examples, using cards (J, Q, A) in seat order:

| Public actions | Net rewards, seats 0/1/2 |
| --- | --- |
| 0 check, 1 check, 2 check | -1, -1, +2 |
| 0 bet, 1 fold, 2 fold | +2, -1, -1 |
| 0 check, 1 bet, 2 call, 0 fold | -1, -2, +3 |
| 0 check, 1 check, 2 bet, 0 call, 1 call | -2, -2, +4 |

## What a player can observe

During a hand, a player sees its own card, the current actor, public betting
actions, contributions and pot, its own legal actions when it is its turn, and
the public seat-to-identity mapping supplied by the session layer. It cannot
see other cards, hidden schedules, audit labels, or complete game state.

At settlement, everyone sees the winner and public actions. If at least two
seats remain active, all their cards are revealed to everyone, including folded
players. Folded cards stay hidden from others. If all opponents fold, the
winner's card also stays hidden. Each player retains knowledge of its own card
and receives only its own explicit net reward. The full reward vector belongs
in the audit. Other rewards may be inferred from public actions and the winner;
we make no claim that their values are secret.

Only cards revealed by these rules are added to public history. Messages may
claim a card, truthfully or falsely; the session layer must not turn a claim
into a verified game-state disclosure. The audit stores the true deal separately.
The engine's raw state string and serialized snapshots are never model inputs.

## Identities, seats, and matched schedules

Player identities A, B, and C persist throughout a session. On hand index `h`
(zero-based), the default seats are `(A, B, C)` rotated left by `h mod 3`:
ABC, BCA, CAB, ABC. Thus each identity acts in each position once per three hands.
A configurable initial offset of 0, 1, or 2 can balance starting position across
independent session blocks. Nonmultiples of three leave residual position
imbalance, which the experiment configuration must account for.

Sample each hand's ordered triple uniformly from the four ranks using a local
seeded random generator. A fresh draw from the full deck is made for each hand;
do not cycle through the 24 deals or remove cards across hands. Save the complete
generated schedule, its schema version, seed, and initial rotation offset.
The saved schedule is authoritative; do not rely on a seed alone across runtime
versions.

Cards in a schedule are indexed by acting seat. For each matched comparison,
reuse both the same seat-indexed cards and the same identity rotation. This
gives each identity the same cards and positions in every condition. Session
histories and decisions remain independent. Do not show players future deals,
the seed, or a matched-block identifier.

## Engine boundary and verification

The wrapper uses OpenSpiel's built-in
[`kuhn_poker(players=3)`](https://openspiel.readthedocs.io/en/latest/api_reference/load_game.html).
It names decisions check/bet/call/fold instead of exposing ambiguous integer
actions. It adds the observation policy above and validates explicit input
before passing it to the native engine.

Versioned game snapshots contain only the exact deal and accepted betting
actions. Restoration validates and replays them through the wrapper. Invalid
deals, illegal actions, actions after termination, extra fields, or unknown
schema versions are rejected. Clones can advance independently. These are game
snapshots; complete session state and recovery are later milestones.

Verification enumerates all 24 ordered deals and all 13 terminal betting paths
per deal: one all-check path, and four call/fold combinations for each of three
possible opening bettors. Expected contributions and winners are independently
specified in the tests. Each path checks intermediate actors and legal actions,
termination, settlement, privacy, and replay. No model calls are involved.
