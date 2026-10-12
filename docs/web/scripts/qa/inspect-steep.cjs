const { chromium, browserChannel } = require("./runtime.cjs");
const fs = require("node:fs");
(async () => {
  const browser = await chromium.launch({
    channel: browserChannel,
    headless: true,
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });
  await page.goto("https://steep.app", {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: ".preview/steep-hero.png" });
  fs.writeFileSync(".preview/steep-source.html", await page.content());
  console.log(
    await page.evaluate(() => ({
      title: document.title,
      headings: [...document.querySelectorAll("h1,h2,h3")].map(
        (x) => x.textContent,
      ),
      scripts: [...document.scripts].map((x) => x.src).filter(Boolean),
      animationClasses: [
        ...document.querySelectorAll(
          '[style*="transform"], [class*="sticky"], [class*="scroll"], [class*="motion"]',
        ),
      ]
        .slice(0, 25)
        .map((x) => ({
          tag: x.tagName,
          cl: x.className,
          style: x.getAttribute("style"),
        })),
    })),
  );
  await page.mouse.wheel(0, 950);
  await page.waitForTimeout(1000);
  await page.screenshot({ path: ".preview/steep-scroll-1.png" });
  await page.mouse.wheel(0, 1100);
  await page.waitForTimeout(1000);
  await page.screenshot({ path: ".preview/steep-scroll-2.png" });
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
