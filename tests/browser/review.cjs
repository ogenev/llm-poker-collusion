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
async function save(page, status, scenario, previous) {
  const pending = page.waitForEvent("download");
  await page.locator(`#export-${status}`).click();
  const download = await pending;
  const output = path.join(directory, download.suggestedFilename());
  await download.saveAs(output);
  await notice(page, "Download requested:");
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
  await pair.locator('.pair-body > label [data-field="explanation"]').fill(expected.explanation);
  await fillInterval(pair.locator(".pair-body > .interval"), expected.interval);
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
    assert.deepEqual(errors, [], "Browser runtime errors");
    assert.deepEqual(requests, [], "Unexpected network requests");
    fs.writeFileSync(path.join(directory, "exports.json"), JSON.stringify(outputs));
    console.log(`Validated browser interactions for six scenarios; ${outputs.length} exports ready for Python validation.`);
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
