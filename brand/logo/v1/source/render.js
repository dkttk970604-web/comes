// generate.py가 만든 작업 목록(JSON)을 Chromium으로 PNG 렌더링합니다.
// usage: node render.js jobs.json   jobs: [{html, out, w, h, transparent, full}]
const path = require('path');
const fs = require('fs');
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

(async () => {
  const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const browser = await chromium.launch();
  for (const j of jobs) {
    const page = await browser.newPage({ viewport: { width: j.w, height: j.h } });
    await page.goto('file://' + path.resolve(j.html));
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: j.out, fullPage: !!j.full, omitBackground: !!j.transparent });
    await page.close();
  }
  await browser.close();
})();
