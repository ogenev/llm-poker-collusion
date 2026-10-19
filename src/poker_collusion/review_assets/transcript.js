const PRIMARY_EVENTS = new Set(["hand_dealt", "decision_requested", "messages_delivered", "action_applied", "rewards_settled", "session_failed", "session_interrupted"]);
const eventHands = new Map();
let currentHand = null;
for (const event of DATA.events) {
  const index = event.data.hand_index ?? event.data.view?.hand_index;
  if (Number.isInteger(index)) currentHand = index;
  eventHands.set(event.sequence, currentHand);
}
function jumpTo(ref) {
  $("hand-filter").value = "all";
  $("all-events").checked = true;
  renderTranscript();
  $(`event-${ref.sequence}`).scrollIntoView({block: "center", behavior: "smooth"});
}
function eventCard(event) {
  const node = el("article", undefined, "event"); node.id = `event-${event.sequence}`;
  const data = event.data;
  node.append(el("div", `#${event.sequence} · ${event.event}`, "event-title"));
  if (BATCHES.includes(event.event)) {
    if (!data.messages.length) node.append(el("p", "No messages in this batch. Describe absence using the reviewed interval.", "hint"));
    data.messages.forEach((message, index) => {
      const messageNode = el("div", undefined, "message");
      messageNode.append(el("strong", `${message.sender} → ${message.recipient ?? "all players"} · round ${message.round_index + 1} · index ${index}`),
        el("p", message.text), button("Cite message", () => cite(reference(event, index))));
      if (event.event === "messages_pending") messageNode.append(el("p", "Pending — not yet delivered.", "hint"));
      node.append(messageNode);
    });
  } else {
    if (event.event === "decision_requested") {
      const view = data.view;
      const timing = view.round_index === null ? view.phase : `round ${view.round_index + 1}`;
      node.append(rawDetails(`Recorded view · ${view.player_id} · ${timing} · own card ${view.poker.own_card}`, view));
    } else if (event.event === "hand_dealt") {
      node.append(el("p", `Hand ${data.hand_index + 1} · seats ${data.seats.join(" / ")}`));
      // The snapshot contains true cards. Never mix it with a player's view.
      let snapshot = data.poker_snapshot;
      try { snapshot = JSON.parse(snapshot); } catch { /* Keep the original audit text. */ }
      node.append(rawDetails("Audit only · true deal (0=J, 1=Q, 2=K, 3=A)", snapshot, true));
    } else if (event.event === "action_applied") {
      node.append(el("p", `${data.player_id} · ${data.action}`));
      node.append(rawDetails("Audit only · action record and full snapshot", data, true));
    } else if (event.event === "rewards_settled") {
      node.append(el("p", Object.entries(data.rewards).map(([player, reward]) => `${player}: ${reward > 0 ? "+" : ""}${reward}`).join(" · ")));
    } else node.append(rawDetails("Audit record · may include information unavailable to players", data, true));
    node.append(button("Cite event", () => cite(reference(event))));
  }
  const range = el("div", undefined, "toolbar");
  for (const bound of ["start", "end"]) range.append(button(`Episode ${bound} here`, () => {
    if (!target) { notice("Choose an episode judgment before setting its interval.", true); return; }
    target.episode.interval[bound] = event.sequence;
    changed(); renderPairs();
    notice(`Episode ${bound} set to #${event.sequence}. Include every cited event within the interval.`);
  }));
  node.append(range);
  return node;
}
function renderTranscript() {
  const container = $("transcript"); container.replaceChildren();
  const filter = $("hand-filter").value;
  let heading = undefined;
  for (const event of DATA.events) {
    const hand = eventHands.get(event.sequence);
    if (filter !== "all" && hand !== Number(filter)) continue;
    if (!$("all-events").checked && !PRIMARY_EVENTS.has(event.event)) continue;
    if (heading !== hand) {
      heading = hand;
      container.append(el("h3", hand === null ? "Session setup" : `Hand ${hand + 1}`, "hand-heading"));
    }
    container.append(eventCard(event));
  }
}
for (const hand of [...new Set(eventHands.values())].filter(value => value !== null)) {
  const option = el("option", `Hand ${hand + 1}`); option.value = String(hand); $("hand-filter").append(option);
}
$("hand-filter").addEventListener("change", renderTranscript);
$("all-events").addEventListener("change", renderTranscript);
