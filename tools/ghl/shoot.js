// Shared: measure targets on the current page and write lessons/shots/<id>.png + _ghl_anchors/<id>.json
const fs = require('fs'); const path = require('path');
const root = path.resolve(__dirname, '../..'), shotsDir = path.join(root, 'lessons/shots'), anchDir = path.join(shotsDir, '_ghl_anchors'); const W = 1600, H = 900;
async function shoot(p, id, targets = [], { mask = [] } = {}) {
  fs.mkdirSync(anchDir, { recursive: true });
  for (const m of mask) for (const fr of p.frames()) await fr.evaluate(sel => { const re = new RegExp(sel, 'i'); document.querySelectorAll('body *').forEach(e => { if (e.children.length === 0 && re.test(e.textContent)) e.style.filter = 'blur(7px)'; }); }, m).catch(() => {}); // masks in every frame (calendar pages live in an iframe)
  const pointers = [];
  for (const t of targets) {
    let b; if (t.rect) b = t.rect; else { const loc = t.find(p).first(); await loc.waitFor({ state: 'visible', timeout: 12000 }); b = await loc.boundingBox(); if (!b) throw new Error('no box for ' + t.label); }
    const cx = t.at === 'left' ? b.x + Math.min(40, b.width / 2) : b.x + b.width / 2, cy = b.y + b.height / 2;
    if (cx < 0 || cx > W - 4 || cy < 0 || cy > H - 20) throw new Error(`target "${t.label}" outside screenshot (${Math.round(cx)},${Math.round(cy)})`);
    const o = { x: +(cx / W).toFixed(4), y: +(cy / H).toFixed(4), label: t.label }; if (t.box) o.box = { w: +Math.min(1, (b.width + 12) / W).toFixed(4), h: +Math.min(1, (b.height + 12) / H).toFixed(4) };
    pointers.push(o);
  }
  await p.screenshot({ path: path.join(shotsDir, id + '.png') });
  fs.writeFileSync(path.join(anchDir, id + '.json'), JSON.stringify({ id, pointers }, null, 2) + '\n');
  return pointers.length;
}
module.exports = { shoot };
