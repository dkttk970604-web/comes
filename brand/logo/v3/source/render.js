// generate.py가 만든 작업 목록(JSON)을 Chromium으로 렌더링합니다.
// job: {html, out?, w, h, transparent?, full?, pdf?, pages?}
//   out   : 화면 캡처 PNG
//   pdf   : 페이지(.page 요소)마다 w x h 크기의 PDF
//   pages : .page 요소를 하나씩 PNG로 저장 (printf 형식 경로, 예: page-%02d.png)
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
    await page.waitForTimeout(100);
    if (j.out) await page.screenshot({ path: j.out, fullPage: !!j.full, omitBackground: !!j.transparent });
    if (j.pages) {
      const els = await page.$$('.page');
      for (let i = 0; i < els.length; i++) {
        await els[i].screenshot({ path: j.pages.replace('%02d', String(i + 1).padStart(2, '0')) });
      }
    }
    if (j.pdf) await page.pdf({ path: j.pdf, width: `${j.w}px`, height: `${j.h}px`, printBackground: true });
    await page.close();
  }
  await browser.close();
})();
