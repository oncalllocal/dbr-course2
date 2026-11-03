// usage: node screenshot.js <html_dir> <out_png_dir> <anchors_dir>
// Screenshots every *.html at 1600x900 and writes <id>.json with normalised bounding boxes of [data-a] elements.
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
(async () => {
  const [htmlDir, outDir, ancDir] = process.argv.slice(2);
  fs.mkdirSync(outDir, { recursive: true }); fs.mkdirSync(ancDir, { recursive: true });
  const br = await chromium.launch(); const pg = await br.newPage({ viewport: { width: 1600, height: 900 } });
  for (const f of fs.readdirSync(htmlDir).filter(f => f.endsWith('.html')).sort()) {
    const id = f.replace(/\.html$/, '');
    await pg.goto('file://' + path.resolve(htmlDir, f)); await pg.waitForTimeout(80);
    const anchors = await pg.evaluate(() => Object.fromEntries([...document.querySelectorAll('[data-a]')].map(e => {
      const r = e.getBoundingClientRect(); return [e.dataset.a, { x: (r.left + r.width / 2) / 1600, y: (r.top + r.height / 2) / 900, w: r.width / 1600, h: r.height / 900 }]; })));
    const overflow = await pg.evaluate(() => document.documentElement.scrollHeight > 900 || document.documentElement.scrollWidth > 1600);
    if (overflow) console.error(`WARNING ${id}: content overflows 1600x900`);
    await pg.screenshot({ path: path.join(outDir, id + '.png') });
    fs.writeFileSync(path.join(ancDir, id + '.json'), JSON.stringify(anchors, null, 1));
    console.log('shot', id, Object.keys(anchors).length, 'anchors');
  }
  await br.close();
})();
