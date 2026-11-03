#!/usr/bin/env node
/**
 * Capture real GHL screens + exact pointer anchors.
 *   node capture.js <scratch> [--only id1,id2] [--list]
 * Manifest: manifest.js (id, rel path, prep(page), targets[{label, find(page), box?, at?}], mask[]).
 * Outputs: lessons/shots/<id>.png (1600x900) and lessons/shots/_ghl_anchors/<id>.json (pointers relative to the image).
 * Guardrails: manifests may open dialogs/menus but must never submit purchases, registrations, messages or domain changes.
 */
const { open, go, settled } = require('./lib'); const fs = require('fs'); const path = require('path');
const SC = process.argv[2]; const only = (process.argv.find(a => a.startsWith('--only=')) || '').slice(7).split(',').filter(Boolean);
const root = path.resolve(__dirname, '../..'), shotsDir = path.join(root, 'lessons/shots'), anchDir = path.join(shotsDir, '_ghl_anchors');
const manifest = require('./manifest');
if (process.argv.includes('--list')) { manifest.forEach(m => console.log(m.id)); process.exit(0); }
const W = 1600, H = 900;
async function blur(p, masks = []) {
  for (const m of masks) await p.evaluate(sel => { const re = sel.startsWith('/') ? new RegExp(sel.slice(1, sel.lastIndexOf('/')), 'i') : null; document.querySelectorAll('body *').forEach(e => { if (e.children.length === 0 && (re ? re.test(e.textContent) : e.matches(sel))) e.style.filter = 'blur(7px)'; }); }, m).catch(() => {});
}
(async () => {
  fs.mkdirSync(anchDir, { recursive: true });
  const { browser, page: p } = await open(SC, { width: W, height: H }); const results = [];
  for (const m of manifest) {
    if (only.length && !only.includes(m.id)) continue;
    try {
      if (m.abs) { await p.goto(m.abs, { waitUntil: 'domcontentloaded', timeout: 60000 }); await settled(p, 45000); }
      if (m.rel) { const ok = await go(p, m.rel, { tries: 2 }); if (!ok) throw new Error('navigation bounced: ' + p.url()); }
      if (m.prep) { await m.prep(p); await p.waitForTimeout(1500); }
      await blur(p, m.mask);
      const pointers = [];
      for (const t of m.targets || []) {
        let b;
        if (t.rect) b = t.rect; // explicit pixel region in the 1600x900 viewport
        else { const loc = t.find(p).first(); await loc.waitFor({ state: 'visible', timeout: 12000 }); await loc.scrollIntoViewIfNeeded().catch(() => {}); await p.waitForTimeout(500); b = await loc.boundingBox(); if (!b) throw new Error('no box for target ' + t.label); }
        const cx = t.at === 'left' ? b.x + Math.min(40, b.width / 2) : b.x + b.width / 2, cy = b.y + b.height / 2;
        if (cx < 0 || cx > W - 4 || cy < 0 || cy > H - 20) throw new Error(`target "${t.label}" is outside the visible screenshot (${Math.round(cx)},${Math.round(cy)})`);
        const o = { x: +(cx / W).toFixed(4), y: +(cy / H).toFixed(4), label: t.label }; if (t.box) o.box = { w: +Math.min(1, (b.width + 12) / W).toFixed(4), h: +Math.min(1, (b.height + 12) / H).toFixed(4) };
        pointers.push(o);
      }
      await p.screenshot({ path: path.join(shotsDir, m.id + '.png') });
      fs.writeFileSync(path.join(anchDir, m.id + '.json'), JSON.stringify({ id: m.id, pointers }, null, 2) + '\n');
      results.push([m.id, 'ok', pointers.length + ' pointer(s)']);
    } catch (e) { await p.screenshot({ path: path.join(SC, 'fail_' + m.id + '.png') }).catch(() => {}); results.push([m.id, 'FAIL', e.message.split('\n')[0].slice(0, 140)]); }
    if (m.cleanup) await m.cleanup(p).catch(() => {}); else await p.keyboard.press('Escape').catch(() => {});
  }
  results.forEach(r => console.log(r.join(' | '))); await browser.close();
  process.exit(results.some(r => r[1] === 'FAIL') ? 1 : 0);
})().catch(e => { console.error('ERR', e.message.slice(0, 250)); process.exit(1); });
