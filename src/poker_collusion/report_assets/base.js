const payload = JSON.parse(document.getElementById("report-data").textContent);
const report = payload.report;
const stages = ["proposed", "accepted", "enacted"];
const names = {none: "No communication", public: "Public", private: "Private"};
const $ = id => document.getElementById(id);
const label = value => value === null || value === undefined ? "Unknown" : String(value).replaceAll("_", " ");
const number = value => value === null ? "Unavailable" : new Intl.NumberFormat("en", {maximumFractionDigits: 2}).format(value);
const percent = value => value === null ? "Unavailable" : `${number(100 * value)}%`;
const difference = (value, metric) => value === null ? "Unavailable" : `${value > 0 ? "+" : ""}${number(stages.includes(metric) ? value * 100 : value)} ${stages.includes(metric) ? "pp" : "chips"}`;
const interval = (estimate, metric) => estimate.interval === null ? "Unavailable" : `${difference(estimate.interval.lower, metric)} to ${difference(estimate.interval.upper, metric)}`;
const confidence = percent(report.policy.bootstrap.confidence);

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function details(parent, title) {
  const node = element("details"); node.append(element("summary", title)); parent.append(node); return node;
}
function list(parent, values) {
  const node = element("ul"); values.forEach(value => node.append(element("li", value))); parent.append(node);
}
function facts(parent, values) {
  for (const [key, value] of values) parent.append(element("dt", key), element("dd", value));
}
function card(parent, title, value, note) {
  const node = element("div", undefined, "card");
  node.append(element("span", title), element("strong", value), element("span", note)); parent.append(node);
}
function table(parent, caption, headings, rows) {
  const wrap = element("div", undefined, "table-wrap"), node = element("table"), head = element("thead"), body = element("tbody"), tr = element("tr");
  node.append(element("caption", caption));
  headings.forEach(title => { const th = element("th", title); th.scope = "col"; tr.append(th); });
  head.append(tr); node.append(head, body); wrap.append(node); parent.append(wrap);
  rows.forEach(values => { const row = element("tr"); values.forEach(value => row.append(element("td", String(value)))); body.append(row); });
}
function badge(value) {
  const known = ["observed", "not_observed", "uncertain"].includes(value) ? value : "unknown";
  return element("span", label(known), `tag ${known}`);
}
function reasons(session) {
  return [...new Set([...session.session_exclusions, ...Object.values(session.stage_exclusions).flat()])];
}
function estimateDetails(parent, estimate) {
  table(parent, "Included matched blocks", ["Block ID", "Left", "Right", "Difference"], estimate.members.map(m => [m.block_id, m.left, m.right, m.difference]));
  if (!estimate.members.length) parent.append(element("p", "No eligible matched blocks."));
  if (estimate.exclusions.length) table(parent, "Excluded matched blocks", ["Block ID", "Reasons by condition"], estimate.exclusions.map(e => [e.block_id, Object.entries(e.reasons).map(([channel, why]) => `${names[channel]}: ${why.map(label).join("; ")}`).join(" · ")]));
}
