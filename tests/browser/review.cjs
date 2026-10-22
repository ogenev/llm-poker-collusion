// Development test only: no browser dependency is included in generated pages.
// These scripted interactions test storage, not human agreement with the rubric.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {pathToFileURL} = require("node:url");
const {chromium} = require("playwright");
const [fixturePath, directory] = process.argv.slice(2);
const fixtures = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
const outputs = [], errors = [], requests = [];
const stages = ["proposed", "accepted", "enacted"];
const localHTTP = process.env.POKER_REVIEW_BROWSER_HTTP === "1";
const read = file => JSON.parse(fs.readFileSync(file, "utf8"));
const copy = object => JSON.parse(JSON.stringify(object));

async function notice(page, text) {
  await page.waitForFunction(text => document.getElementById("notice").textContent.includes(text), text);
}
async function save(page, status, scenario, previous, form = page) {
  const pending = page.waitForEvent("download");
  await form.locator(`#export-${status}`).click();
  const download = await pending;
  const output = path.join(directory, download.suggestedFilename());
  await download.saveAs(output);
  await notice(form, "Download requested:");
  outputs.push({path: output, scenario, previous});
  return output;
}
async function upload(page, content, name = "review.json") {
  await page.locator("#import-review").setInputFiles({name, mimeType: "application/json", buffer: Buffer.from(content)});
}
async function importFile(page, file) {
  await page.locator("#import-review").setInputFiles(file);
  await notice(page, "Imported human review");
}
async function fillInterval(locator, interval) {
  await locator.locator('[data-bound="start"]').fill(String(interval.start));
  await locator.locator('[data-bound="end"]').fill(String(interval.end));
}
async function fillPair(page, expected) {
  const pair = page.locator(`.pair[data-pair="${expected.pair.join("")}"]`);
  if (!await pair.evaluate(node => node.open)) await pair.locator(":scope > summary").click();
  await pair.locator('[data-field="coverage"]').selectOption(expected.coverage);
  if (expected.coverage === "no_candidate") {
    assert.equal(await pair.locator('[data-bound]').count(), 0);
    if (expected.explanation) {
      await pair.getByText("Notes (optional)", {exact: true}).click();
      await pair.getByLabel("Optional notes", {exact: true}).fill(expected.explanation);
    }
  } else {
    await pair.locator('.pair-body > label [data-field="explanation"]').fill(expected.explanation);
    await fillInterval(pair.locator(".pair-body > .interval"), expected.interval);
  }
  for (let index = 0; index < expected.episodes.length; index++) {
    if (index > 0) await pair.getByRole("button", {name: "Add episode", exact: true}).click();
    const actual = pair.locator(".episode").nth(index), episode = expected.episodes[index];
    await fillInterval(actual.locator(":scope > .interval"), episode.interval);
    await actual.locator('[data-field="arrangement"]').fill(episode.arrangement);
    for (const stage of stages) {
      const form = actual.locator(`fieldset[data-stage="${stage}"]`), judgment = episode[stage];
      if (judgment === null) continue;
      await form.locator('[data-field="verdict"]').selectOption(judgment.verdict);
      await form.locator('[data-field="explanation"]').fill(judgment.explanation);
      await form.locator('[data-field="alternatives"]').fill(judgment.alternatives);
      await form.getByRole("button", {name: "Choose evidence", exact: true}).click();
      for (const field of ["supporting_evidence", "contradicting_evidence"]) {
        await page.locator("#evidence-kind").selectOption(field);
        for (const ref of judgment[field]) {
          const event = page.locator(`#event-${ref.sequence}`);
          if (ref.message === null) await event.getByRole("button", {name: "Cite event", exact: true}).click();
          else await event.locator(".message").nth(ref.message.index).getByRole("button", {name: "Cite message", exact: true}).click();
          await notice(page, "Added");
        }
      }
    }
  }
}
async function main() {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_PATH || undefined});
  try {
    const context = await browser.newContext({acceptDownloads: true, viewport: {width: 1440, height: 1050}});
    // Some managed browsers forbid file://. In that environment only, fulfill
    // the exact generated HTML at localhost without a server or outbound request.
    await context.route("**/*", route => {
      const url = route.request().url();
      if (url === "http://localhost/coverage-preview.html") return route.fulfill({contentType: "text/html", body:
        '<iframe title="Review preview" sandbox="allow-scripts allow-same-origin allow-downloads" src="/coverage-review.html" style="width:1400px;height:1000px"></iframe>'});
      if (url === "http://localhost/coverage-review.html") return route.fulfill({contentType: "text/html", body: fs.readFileSync(fixtures[0].page)});
      const match = /^http:\/\/localhost\/review-(\d+)\.html$/.exec(url);
      if (localHTTP && match && fixtures[Number(match[1])]) return route.fulfill({contentType: "text/html", body: fs.readFileSync(fixtures[Number(match[1])].page)});
      requests.push(url); return route.abort();
    });
    async function open(index) {
      const page = await context.newPage();
      page.setDefaultTimeout(10000);
      page.on("pageerror", error => errors.push(error.message));
      page.on("dialog", dialog => dialog.accept());
      await page.goto(localHTTP ? `http://localhost/review-${index}.html` : pathToFileURL(fixtures[index].page).href);
      assert.equal(await page.locator(".pair").count(), 3);
      return page;
    }
    for (let index = 0; index < fixtures.length; index++) {
      let page = await open(index);
      const expected = read(fixtures[index].annotation);
      assert.equal(await page.locator(".episode").count(), 0);
      assert.equal(await page.locator("#reviewer-id").inputValue(), "");
      await page.locator("#reviewer-id").fill("automated-browser-test-fixture");
      await page.locator("#export-complete").click();
      await notice(page, "still unreviewed");
      const draft = await save(page, "draft", index, null);
      assert(read(draft).pair_reviews.every(pair => pair.coverage === "unreviewed"));
      const retry = page.waitForEvent("download");
      await page.locator("#download-previous").click();
      const retryPath = path.join(directory, `retry-${index}.json`);
      await (await retry).saveAs(retryPath);
      assert.deepEqual(fs.readFileSync(retryPath), fs.readFileSync(draft));
      await page.locator("#all-events").check();
      await page.locator("#hand-filter").selectOption("0");
      await page.locator("#hand-filter").selectOption("all");
      assert(await page.getByText(/Recorded view · A/).count() > 0);
      assert(await page.getByText(/Audit only · true deal/).count() > 0);
      for (const pair of expected.pair_reviews) await fillPair(page, pair);
      if (index === 5) await page.screenshot({path: path.join(directory, "review-desktop.png"), fullPage: true});
      const complete = await save(page, "complete", index, draft);
      const saved = read(complete);
      // IDs are created by the UI; all labels, rationale, and exact evidence match.
      const normalized = copy(saved.pair_reviews);
      for (let p = 0; p < normalized.length; p++) normalized[p].episodes.forEach((episode, e) => {
        episode.episode_id = expected.pair_reviews[p].episodes[e].episode_id;
      });
      assert.deepEqual(normalized, expected.pair_reviews);
      assert.equal(saved.reviewer.kind, "human");
      await page.close();
      page = await open(index);
      await importFile(page, complete);
      assert(await page.locator("#reviewer-id").isDisabled());
      const revision = await save(page, "complete", index, complete);
      assert.deepEqual(read(revision).pair_reviews, saved.pair_reviews);
      // Failed imports leave the loaded review and its predecessor untouched.
      const malformed = copy(saved); malformed.source.sha256 = "0".repeat(64);
      await upload(page, JSON.stringify(malformed)); await notice(page, "Source mismatch");
      await upload(page, JSON.stringify(saved).replace('"version":1', '"version":1,"version":1'));
      await notice(page, "duplicate key");
      await page.locator("#import-review").setInputFiles(fixtures[index].annotation);
      await notice(page, "human reviews only");
      assert.equal(await page.locator("#reviewer-id").inputValue(), "automated-browser-test-fixture");
      const afterRejections = await save(page, "complete", index, revision);
      assert.deepEqual(read(afterRejections).pair_reviews, saved.pair_reviews);
      if (index === 5) {
        // Malicious-looking IDs and prose remain text and do not become selectors or HTML.
        const unusual = copy(saved);
        unusual.annotation_id = "unusual-test-input"; unusual.supersedes = null;
        unusual.created_at = "2100-01-01T00:00:00.123456Z";
        unusual.pair_reviews[0].episodes[0].episode_id = 'episode" ] <img src=x onerror="globalThis.injected=1">';
        unusual.pair_reviews[0].explanation += '\n</script><img src=x onerror="globalThis.injected=1">';
        const unusualFile = path.join(directory, "unusual.json"); fs.writeFileSync(unusualFile, JSON.stringify(unusual) + "\n");
        await importFile(page, unusualFile);
        await save(page, "complete", index, unusualFile);
        assert.equal(await page.evaluate(() => globalThis.injected), undefined);
        assert.equal(await page.locator("#pairs img").count(), 0);
        const broken = copy(saved);
        broken.pair_reviews[0].episodes[0].proposed.supporting_evidence[0].sequence = 99999;
        await upload(page, JSON.stringify(broken)); await notice(page, "outside its episode");
        await page.locator("#new-review").click();
        assert.equal(await page.locator(".episode").count(), 0);
        assert(!await page.locator("#reviewer-id").isDisabled());
        await page.locator("#reviewer-id").fill("automated-browser-test-fixture");
        const partial = copy(expected.pair_reviews[0]);
        partial.episodes.push(copy(partial.episodes[0]));
        for (const episode of partial.episodes) for (const stage of stages) episode[stage] = null;
        await fillPair(page, partial);
        const field = page.locator('.episode').first().locator('fieldset[data-stage="proposed"]');
        await field.locator('[data-field="explanation"]').fill("Unfinished note must not disappear");
        await page.locator("#export-draft").click(); await notice(page, "choose observed");
        assert.equal(await field.locator('[data-field="explanation"]').inputValue(), "Unfinished note must not disappear");
        await field.locator('[data-field="explanation"]').fill("");
        await save(page, "draft", index, null);
        await page.setViewportSize({width: 390, height: 844});
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        assert(await page.locator("#pairs").evaluate(node => node.clientHeight >= 360), "Mobile review fields need a usable scroll area");
        await page.screenshot({path: path.join(directory, "review-mobile.png"), fullPage: true});
      }
      await page.close();
    }
    // A reviewer can complete an absence review with three choices and no prose.
    let page = await open(0);
    await page.locator("#reviewer-id").fill("automated-browser-test-fixture");
    for (const pair of await page.locator(".pair").all()) {
      if (!await pair.evaluate(node => node.open)) await pair.locator(":scope > summary").click();
      await pair.locator('[data-field="coverage"]').selectOption("no_candidate");
      assert.equal(await pair.locator('[data-bound]').count(), 0);
      assert.equal(await pair.locator('textarea:visible').count(), 0);
      assert((await pair.innerText()).includes("Whole session reviewed"));
    }
    const noCandidate = await save(page, "complete", 0, null);
    const saved = read(noCandidate);
    const wholeInterval = read(fixtures[0].annotation).pair_reviews[0].interval;
    for (const pair of saved.pair_reviews) {
      assert.equal(pair.coverage, "no_candidate");
      assert.equal(pair.explanation, "");
      assert.deepEqual(pair.episodes, []);
      assert.deepEqual(pair.interval, wholeInterval);
    }
    await page.close();
    page = await open(0);
    await importFile(page, noCandidate);
    const resumed = await save(page, "complete", 0, noCandidate);
    assert.deepEqual(read(resumed).pair_reviews, saved.pair_reviews);

    // Old partial drafts must never become full-session negatives just by import.
    const partial = copy(saved);
    partial.annotation_id = "partial-no-candidate-test"; partial.review_status = "draft";
    partial.pair_reviews[0].interval = {start: 1, end: wholeInterval.end - 1};
    partial.pair_reviews[0].explanation = "Existing optional notes survive import.";
    const partialFile = path.join(directory, "partial-no-candidate.json");
    fs.writeFileSync(partialFile, JSON.stringify(partial) + "\n");
    await importFile(page, partialFile);
    const pair = page.locator('.pair[data-pair="AB"]');
    assert.equal(await pair.locator('[data-bound]').count(), 0);
    assert.equal(await pair.getByLabel("Optional notes", {exact: true}).inputValue(), partial.pair_reviews[0].explanation);
    const preserved = await save(page, "draft", 0, partialFile);
    assert.deepEqual(read(preserved).pair_reviews, partial.pair_reviews);
    await page.locator("#export-complete").click(); await notice(page, "entire saved journal");
    await pair.getByRole("button", {name: "Mark whole session reviewed", exact: true}).click();
    const completed = await save(page, "complete", 0, preserved);
    assert.deepEqual(read(completed).pair_reviews[0].interval, wholeInterval);
    assert.equal(read(completed).pair_reviews[0].explanation, partial.pair_reviews[0].explanation);
    await page.close();

    // Embedded previews can suppress confirm(). Coverage switching must still work.
    const preview = await context.newPage();
    preview.on("pageerror", error => errors.push(error.message));
    const blockedDialogs = [];
    preview.on("console", message => {
      if (message.text().includes("Ignored call to 'confirm()'")) blockedDialogs.push(message.text());
    });
    await preview.goto("http://localhost/coverage-preview.html");
    await preview.frameLocator("iframe").locator(".pair").first().waitFor();
    const form = preview.frame({url: "http://localhost/coverage-review.html"});
    await form.locator("#reviewer-id").fill("automated-browser-test-fixture");
    for (const key of ["AB", "AC", "BC"]) {
      const pair = form.locator(`.pair[data-pair="${key}"]`);
      if (!await pair.evaluate(node => node.open)) await pair.locator(":scope > summary").click();
      const coverage = pair.locator('[data-field="coverage"]');
      await coverage.selectOption("no_candidate");
      await coverage.selectOption("episodes");
      assert.equal(await pair.locator(".episode").count(), 1);
      await coverage.selectOption("no_candidate");
      assert.equal(await coverage.inputValue(), "no_candidate");
      assert.equal(await pair.locator(".episode, .coverage-confirmation, [data-bound]").count(), 0);
      await coverage.selectOption("episodes");
      await coverage.selectOption("unreviewed");
      assert.equal(await coverage.inputValue(), "unreviewed");
      await coverage.selectOption("no_candidate");
    }
    const firstPair = form.locator('.pair[data-pair="AB"]');
    const coverage = firstPair.locator('[data-field="coverage"]');
    await coverage.selectOption("episodes");
    const arrangement = firstPair.locator('[data-field="arrangement"]');
    await arrangement.fill("Preserve this entered candidate until I explicitly discard it.");
    await firstPair.locator('[data-stage="proposed"]').getByRole("button", {name: "Choose evidence"}).click();
    await coverage.selectOption("no_candidate");
    assert.equal(await coverage.inputValue(), "episodes");
    await firstPair.getByRole("button", {name: "Keep candidate episodes"}).click();
    assert.equal(await arrangement.inputValue(), "Preserve this entered candidate until I explicitly discard it.");
    assert.equal(await firstPair.locator(".coverage-confirmation").count(), 0);
    await coverage.selectOption("unreviewed");
    assert((await firstPair.locator(".coverage-confirmation").innerText()).includes("Switching to unreviewed"));
    await coverage.selectOption("no_candidate");
    assert.equal(await firstPair.locator(".coverage-confirmation").count(), 1);
    assert((await firstPair.locator(".coverage-confirmation").innerText()).includes("Switching to no candidate"));
    await firstPair.getByRole("button", {name: "Discard episodes and switch"}).click();
    assert.equal(await coverage.inputValue(), "no_candidate");
    assert.equal(await firstPair.locator(".episode, .coverage-confirmation").count(), 0);
    assert((await form.locator("#citation-target").innerText()).includes("Select a judgment"));

    // An edited episode range also counts as work even if prose is still empty.
    await coverage.selectOption("episodes");
    await firstPair.locator('.episode [data-bound="start"]').fill("1");
    await coverage.selectOption("no_candidate");
    await firstPair.getByRole("button", {name: "Keep candidate episodes"}).click();
    assert.equal(await firstPair.locator('.episode [data-bound="start"]').inputValue(), "1");
    await coverage.selectOption("no_candidate");
    await firstPair.getByRole("button", {name: "Discard episodes and switch"}).click();
    const switched = await save(preview, "complete", 0, null, form);
    assert(read(switched).pair_reviews.every(pair => pair.coverage === "no_candidate" && !pair.episodes.length && !pair.explanation));
    assert.deepEqual(blockedDialogs, []);
    await preview.close();
    assert.deepEqual(errors, [], "Browser runtime errors");
    assert.deepEqual(requests, [], "Unexpected network requests");
    fs.writeFileSync(path.join(directory, "exports.json"), JSON.stringify(outputs));
    console.log(`Validated browser interactions for six scenarios; ${outputs.length} exports ready for Python validation.`);
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
