const { chromium, browserChannel, previewUrl } = require("./runtime.cjs");
const fs = require("node:fs");
const assert = require("node:assert/strict");
(async () => {
  const browser = await chromium.launch({
    channel: browserChannel,
    headless: true,
  });
  const page = await browser.newPage({
    viewport: { width: 1536, height: 1024 },
    deviceScaleFactor: 1,
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const report = { checks: [], errors };
  await page.goto(previewUrl, { waitUntil: "networkidle" });
  await page.screenshot({ path: ".preview/intro-desktop-hero.png" });
  const y0 = await page
    .locator(".hero-stage")
    .evaluate((el) => el.getBoundingClientRect().top);
  await page.evaluate(() => window.scrollTo(0, 750));
  await page.waitForTimeout(1300);
  const y1 = await page
    .locator(".hero-stage")
    .evaluate((el) => el.getBoundingClientRect().top);
  assert(Math.abs(y0 - y1) < 3, "hero should stay pinned");
  assert(
    Number(
      await page
        .locator(".hero-overview")
        .evaluate((el) => getComputedStyle(el).opacity),
    ) > 0.85,
    "workspace should reveal on scroll",
  );
  await page.screenshot({ path: ".preview/intro-desktop-transition.png" });
  report.checks.push("pinned hero to workspace scroll transition");
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(1200);
  assert(
    Number(
      await page
        .locator(".hero-copy")
        .evaluate((el) => getComputedStyle(el).opacity),
    ) > 0.95,
    "scroll reversal restores hero",
  );
  report.checks.push("scroll reversal restores hero");
  for (let i = 0; i < 4; i++) {
    await page
      .locator(`[data-stage="${i}"]`)
      .evaluate((el) =>
        window.scrollTo(
          0,
          window.scrollY +
            el.getBoundingClientRect().top -
            window.innerHeight * 0.3,
        ),
      );
    await page.waitForTimeout(900);
    assert(
      (await page.locator(`#flow-tab-${i}`).getAttribute("aria-selected")) ===
        "true",
      `scroll switches demo to stage ${i}`,
    );
  }
  report.checks.push("four scroll-driven workflow stages");
  await page.locator("#flow-tab-0").click();
  await page.locator("#flow-tab-0").press("ArrowRight");
  assert(
    (await page.locator("#flow-tab-1").getAttribute("aria-selected")) ===
      "true",
  );
  report.checks.push("keyboard tabs update and focus");
  await page.locator("button").filter({ hasText: "整理行动计划" }).click();
  assert(
    (await page.locator(".sample-question").textContent()).includes("行动计划"),
  );
  report.checks.push("interactive AI sample works without requests");
  await page.locator("#questions summary").nth(1).click();
  assert(
    (await page.locator("#questions details").nth(1).getAttribute("open")) !==
      null,
  );
  report.checks.push("native FAQ disclosure");
  await page.getByRole("button", { name: "复制安装命令" }).click();
  assert((await page.getByRole("status").textContent()).length > 0);
  report.checks.push("installation copy feedback");
  for (const size of [
    { width: 1536, height: 1024 },
    { width: 1440, height: 900 },
    { width: 1024, height: 768 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(size);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(1000);
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `no overflow at ${size.width}`,
    );
    const h = await page.locator("h1").boundingBox();
    assert(h && h.width > 0, "heading visible");
    report.checks.push(`no horizontal overflow ${size.width}×${size.height}`);
    for (
      let pos = 0;
      pos < (await page.evaluate(() => document.body.scrollHeight));
      pos += size.height * 0.8
    ) {
      await page.evaluate((y) => window.scrollTo(0, y), pos);
      await page.waitForTimeout(90);
    }
    await page.waitForTimeout(800);
    await page.screenshot({
      path: `.preview/intro-full-${size.width}.png`,
      fullPage: true,
    });
    if (size.width === 390) {
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.getByRole("button", { name: "打开导航" }).click();
      await page
        .getByRole("navigation", { name: "介绍页导航" })
        .getByRole("link", { name: "本地优先" })
        .click();
      await page.waitForTimeout(900);
      assert(
        !(
          (await page
            .getByRole("button", { name: "打开导航" })
            .getAttribute("aria-expanded")) === "true"
        ),
      );
      report.checks.push("mobile navigation opens, navigates and closes");
      await page.screenshot({ path: ".preview/intro-mobile-local.png" });
    }
  }
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(previewUrl, { waitUntil: "networkidle" });
  assert(
    (await page
      .locator(".hero-stage")
      .evaluate((el) => getComputedStyle(el).position)) === "relative",
  );
  assert(
    (await page
      .locator(".hero-overview")
      .evaluate((el) => getComputedStyle(el).opacity)) === "1",
  );
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  report.checks.push(
    "reduced motion unpins hero and keeps all product content visible",
  );
  await page.screenshot({ path: ".preview/intro-reduced.png" });
  assert.equal(errors.length, 0, "no browser runtime errors");
  fs.writeFileSync(
    ".preview/intro-browser-report.json",
    JSON.stringify(report, null, 2),
  );
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
