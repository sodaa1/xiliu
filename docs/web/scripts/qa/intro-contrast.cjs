const { chromium, browserChannel, previewUrl } = require("./runtime.cjs");
const fs = require("node:fs");
const selectors = [
  ".hero-description",
  ".eyebrow",
  ".manifesto-body p",
  ".workflow-step > p",
  ".step-tags span",
  ".flow-tabs button",
  ".demo-caption",
  ".feature-copy > p:not(.eyebrow)",
  ".inline-benefits",
  ".scene-caption",
  ".ai-demo-sidebar > p",
  ".ai-demo-sidebar > small",
  ".chat-demo-label > small",
  ".sample-answer ol",
  ".question-options button",
  ".everyday-top > p",
  ".everyday-card-title",
  ".everyday-card > p",
  ".local-callout .eyebrow",
  ".local-callout > div:first-child > p:not(.eyebrow)",
  ".local-principles p",
  ".local-footnote",
  ".faq-list details > p",
  ".start-section > div:first-child > small",
  ".install-head",
  ".install-head button",
  ".install-panel > p",
  ".footer-top > p",
  ".footer-top .text-link",
  ".footer-bottom",
];
(async () => {
  const browser = await chromium.launch({
    channel: browserChannel,
    headless: true,
  });
  const page = await browser.newPage({
    viewport: { width: 1536, height: 1024 },
    reducedMotion: "reduce",
  });
  await page.goto(previewUrl, { waitUntil: "networkidle" });
  const results = await page.evaluate((selectors) => {
    const rgb = (color) => color.match(/[\d.]+/g).map(Number);
    const luminance = (channels) =>
      channels
        .slice(0, 3)
        .map((c) => c / 255)
        .map((c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
        .reduce((sum, c, i) => sum + c * [0.2126, 0.7152, 0.0722][i], 0);
    return selectors.map((selector) => {
      const el = document.querySelector(selector);
      if (!el) throw new Error(`Missing selector ${selector}`);
      let ancestor = el,
        background = "rgb(255, 255, 255)";
      while (ancestor) {
        const candidate = getComputedStyle(ancestor).backgroundColor;
        const channels = rgb(candidate);
        if (channels.length === 3 || channels[3] === 1) {
          background = candidate;
          break;
        }
        ancestor = ancestor.parentElement;
      }
      const foreground = getComputedStyle(el).color;
      const a = luminance(rgb(foreground)),
        b = luminance(rgb(background));
      const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
      return {
        selector,
        foreground,
        background,
        ratio: +ratio.toFixed(2),
        pass: ratio >= 4.5,
      };
    });
  }, selectors);
  fs.writeFileSync(
    ".preview/intro-contrast-report.json",
    JSON.stringify(results, null, 2),
  );
  console.log(
    JSON.stringify(
      {
        checked: results.length,
        failures: results.filter((r) => !r.pass),
        minimumRatio: Math.min(...results.map((r) => r.ratio)),
      },
      null,
      2,
    ),
  );
  await browser.close();
  if (results.some((r) => !r.pass)) process.exitCode = 1;
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
