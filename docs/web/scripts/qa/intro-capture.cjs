const { chromium, browserChannel, previewUrl } = require("./runtime.cjs");
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
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(previewUrl, { waitUntil: "networkidle" });
  await page.screenshot({ path: ".preview/intro-final-hero.png" });
  for (const [name, selector] of [
    ["workflow", ".workflow-layout"],
    ["feed", ".feed-section"],
    ["ai", ".ai-demo"],
    ["local", ".local-callout"],
    ["start", ".start-section"],
  ]) {
    await page
      .locator(selector)
      .evaluate((el) =>
        window.scrollTo({
          top: window.scrollY + el.getBoundingClientRect().top - 130,
          behavior: "instant",
        }),
      );
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `.preview/intro-final-${name}.png` });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(previewUrl, { waitUntil: "networkidle" });
  await page.screenshot({ path: ".preview/intro-final-mobile-hero.png" });
  await page.getByRole("button", { name: "打开导航" }).click();
  await page.keyboard.press("Escape");
  assert(
    (await page
      .getByRole("button", { name: "打开导航" })
      .getAttribute("aria-expanded")) === "false",
  );
  assert(
    await page
      .getByRole("button", { name: "打开导航" })
      .evaluate((el) => el === document.activeElement),
  );
  await page
    .locator(".ai-demo")
    .evaluate((el) =>
      window.scrollTo({
        top: window.scrollY + el.getBoundingClientRect().top - 90,
        behavior: "instant",
      }),
    );
  await page.waitForTimeout(900);
  await page.screenshot({ path: ".preview/intro-final-mobile-ai.png" });
  assert.equal(errors.length, 0);
  console.log(
    "Final section captures, console errors, mobile Escape/focus: passed",
  );
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
