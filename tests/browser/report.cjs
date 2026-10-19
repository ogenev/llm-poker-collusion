const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {pathToFileURL} = require("node:url");
const {chromium} = require("playwright");
const [fixturePath, directory] = process.argv.slice(2);
const fixtures = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
const localHTTP = process.env.POKER_REVIEW_BROWSER_HTTP === "1";

async function main() {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_PATH || undefined});
  const errors = [], requests = [];
  try {
    const context = await browser.newContext({viewport: {width: 1440, height: 1080}});
    const pages = new Map(fixtures.reports.map(row => [`/${row.case}.html`, row.path]));
    pages.set("/source review.html", fixtures.source_page);
    // The managed browser forbids file://. Fulfill the exact local artifacts at
    // localhost in that environment; no server or outbound request is needed.
    await context.route("**/*", route => {
      const url = new URL(route.request().url());
      const file = url.origin === "http://localhost" ? pages.get(decodeURIComponent(url.pathname)) : undefined;
      if (localHTTP && file) return route.fulfill({contentType: "text/html", body: fs.readFileSync(file)});
      requests.push(url.href); return route.abort();
    });
    async function open(name) {
      const file = fixtures.reports.find(row => row.case === name).path;
      const page = await context.newPage();
      page.setDefaultTimeout(10000);
      page.on("pageerror", error => errors.push(error.message));
      await page.goto(localHTTP ? `http://localhost/${name}.html` : pathToFileURL(file).href);
      await page.locator("#loading").waitFor({state: "hidden"});
      return page;
    }
    let page = await open("base");
    assert.equal(await page.locator("#session-table tbody tr").count(), 9);
    assert((await page.locator("#primary-cards").innerText()).includes("0 pp"));
    assert((await page.locator("#primary-warnings").innerText()).includes("zero-width"));
    assert.equal(await page.locator("#comparison-chart svg").count(), 1);
    assert.equal(await page.locator("#comparison-chart circle").getAttribute("cx"), "320");
    await page.screenshot({path: path.join(directory, "report-desktop.png")});
    await page.close();

    page = await open("mixed");
    const fixed = await page.locator("#primary").innerText();
    assert(fixed.includes("+100 pp") && fixed.includes("1 / 3") && fixed.includes("Unavailable"));
    assert.equal(await page.locator("#comparison-chart line.interval").count(), 0);
    assert.equal(await page.locator("#comparison-chart circle").getAttribute("cx"), "585");
    await page.locator("#channel-filter").selectOption("private");
    assert.equal(await page.locator("#session-table tbody tr").count(), 3);
    await page.locator("#exclusion-filter").selectOption({label: "uncertain"});
    assert.equal(await page.locator("#session-table tbody tr").count(), 1);
    assert((await page.locator("#session-table tbody").innerText()).includes("block-1-private"));
    await page.locator("#search").fill("no-such-session");
    assert(await page.locator("#empty-sessions").isVisible());
    assert.equal(await page.locator("#primary").innerText(), fixed);
    await page.locator("#reset-filters").click();
    await page.locator("#review-filter").selectOption("draft");
    assert.equal(await page.locator("#session-table tbody tr").count(), 1);
    assert((await page.locator("#session-table tbody").innerText()).includes("block-2-public"));
    await page.locator("#reset-filters").click();
    await page.locator("#status-filter").selectOption("missing");
    assert.equal(await page.locator("#session-table tbody tr").count(), 1);
    await page.locator("#session-table button").click();
    assert((await page.locator("#session-detail").innerText()).includes("No session analysis is available"));
    await page.locator("#reset-filters").click();
    await page.locator("#search").fill("block-0-private");
    await page.locator("#session-table button").click();
    const detail = page.locator("#session-detail");
    assert((await detail.innerText()).includes("globalThis.injected"));
    await detail.getByText("Pair A + B · episodes", {exact: true}).click();
    await detail.locator(".evidence").first().getByText("proposed · observed", {exact: true}).click();
    assert((await detail.innerText()).includes("event #0 · session started"));
    assert((await detail.innerText()).includes("Alternatives considered"));
    assert.equal(await page.locator("img").count(), 0);
    assert.equal(await page.evaluate(() => globalThis.injected), undefined);
    assert.equal(await page.locator("#primary").innerText(), fixed);
    const popupEvent = page.waitForEvent("popup");
    await detail.getByRole("link", {name: "Open source review page"}).click();
    const popup = await popupEvent;
    await popup.waitForLoadState();
    assert.equal(await popup.locator(".pair").count(), 3);
    await popup.close();
    await page.setViewportSize({width: 390, height: 844});
    await page.locator("#primary").scrollIntoViewIfNeeded();
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({path: path.join(directory, "report-mobile.png")});
    await page.emulateMedia({media: "print"});
    assert(await page.locator("#primary").isVisible());
    assert(!(await page.locator("#session-table").isVisible()));
    await page.close();

    page = await open("unreviewed");
    assert.equal(await page.locator("#comparison-chart svg").count(), 0);
    assert((await page.locator("#comparison-chart").innerText()).includes("No eligible matched blocks"));
    assert((await page.locator("#primary-cards").innerText()).includes("0 / 3"));
    await page.locator("#review-filter").selectOption("unreviewed");
    assert.equal(await page.locator("#session-table tbody tr").count(), 9);
    await page.close();

    page = await open("large");
    assert.equal(await page.locator("#session-table tbody tr").count(), 25);
    await page.locator("#next-page").click();
    assert.equal(await page.locator("#session-table tbody tr").count(), 5);
    await page.locator("#channel-filter").selectOption("private");
    assert.equal(await page.locator("#session-table tbody tr").count(), 10);
    assert.equal(await page.locator("#page-number").innerText(), "Page 1 of 1");
    await page.close();

    page = await open("failed");
    await page.locator("#status-filter").selectOption("failed");
    assert.equal(await page.locator("#session-table tbody tr").count(), 3);
    await page.locator("#session-table button").first().click();
    assert((await page.locator("#session-detail").innerText()).includes("Recorded failure"));
    assert((await page.locator("#primary-cards").innerText()).includes("0 / 1"));
    await page.close();
    assert.deepEqual(errors, [], "Browser runtime errors");
    assert.deepEqual(requests, [], "Unexpected requests");
    console.log("Report browser checks passed: fixed estimates, filters, evidence, links, missing/failed data, pagination, mobile, and print.");
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
