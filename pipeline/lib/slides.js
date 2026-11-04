// HTML for each slide type + transparent overlay assets (arrow, ring, box, label).
const fs = require('fs'), path = require('path');
const root = path.resolve(__dirname, '../..');
const css = fs.readFileSync(path.join(__dirname, '../theme.css'), 'utf8') + `
.shot-title{position:absolute;left:60px;top:34px;font-size:46px;font-weight:800;color:var(--blue)}
.frame{position:absolute;left:60px;top:116px;width:1800px;height:830px;background:#fff;border-radius:18px;box-shadow:0 12px 40px rgba(0,67,122,.22);overflow:hidden;display:flex;align-items:center;justify-content:center}
.frame img{max-width:100%;max-height:100%;display:block}
.ph{width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;background:repeating-linear-gradient(45deg,#fff6ec,#fff6ec 24px,#fdeeda 24px,#fdeeda 48px);color:var(--ink);text-align:center;padding:60px}
.ph b{font-size:44px;color:var(--orange);letter-spacing:.08em}.ph p{font-size:34px;line-height:1.4;max-width:1400px;margin-top:24px}
`;
const logo = 'data:image/png;base64,' + fs.readFileSync(path.join(root, 'brand/logo.png')).toString('base64');
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const hl = s => esc(s).replace(/\*(.+?)\*/g, '<em>$1</em>');
const mime = f => (/\.jpe?g$/i.test(f) ? 'image/jpeg' : /\.webp$/i.test(f) ? 'image/webp' : 'image/png');

function slideHtml(lesson, s, imgPath) {
  const footText = lesson.footer !== undefined ? lesson.footer : `${lesson.id} · ${lesson.title}`;
  const note = s.note ? `<div class="note">${esc(s.note)}</div>` : '';
  const foot = `${note}<div class="foot">${esc(footText)}</div><img class="logo" src="${logo}">`;
  let body = '', cls = '';
  if (s.type === 'title') { cls = 'hero'; body = `<div class="wrap"><h1>${hl(s.title)}</h1><div class="sub">${esc(s.sub || '')}</div></div>`; }
  else if (s.type === 'bullets') body = `<div class="wrap"><h2>${hl(s.title)}</h2><ul>${s.items.map(i => `<li>${hl(i)}</li>`).join('')}</ul></div>`;
  else if (s.type === 'stat') body = `<div class="wrap"><div class="stat">${esc(s.big)}</div><div class="statlbl">${hl(s.label)}</div></div>`;
  else if (s.type === 'cols') body = `<div class="wrap"><h2>${hl(s.title)}</h2><div class="cols">${s.cards.map((c, i) => `<div class="card ${i % 2 ? 'o' : ''}"><h3>${esc(c.h)}</h3><p>${esc(c.p)}</p></div>`).join('')}</div></div>`;
  else if (s.type === 'clip') body = '';
  else if (s.type === 'quote') body = `<div class="wrap"><div class="quote">${hl(s.text)}</div></div>`;
  else if (s.type === 'shot') {
    const inner = imgPath ? `<img id="shot" src="data:${mime(imgPath)};base64,${fs.readFileSync(imgPath).toString('base64')}">`
      : `<div class="ph" id="shot"><b>SCREENSHOT NEEDED</b><p>${esc(s.capture)}</p><p style="font-size:26px;color:var(--mute)">${esc(s.image)}</p></div>`;
    body = `<div class="shot-title">${hl(s.title || '')}</div><div class="frame" id="frame">${inner}</div>`;
  }
  return `<html><head><meta charset="utf-8"><style>${css}</style></head><body class="${cls}"><div class="bar"></div>${body}${foot}</body></html>`;
}

/** Displayed rect of the screenshot (or placeholder) in slide pixels. */
async function shotRect(page) {
  return page.evaluate(() => { const r = document.getElementById('shot').getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; });
}

const ARROW = { w: 110, h: 130, tipX: 14, tipY: 12 }, RING = 120;
const arrowSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="${ARROW.w}" height="${ARROW.h}" viewBox="0 0 110 130"><defs><filter id="s" x="-30%" y="-30%" width="180%" height="180%"><feDropShadow dx="3" dy="5" stdDeviation="4" flood-opacity=".4"/></filter></defs><path filter="url(#s)" d="M14 12 L14 100 L36 80 L52 118 L70 110 L54 73 L84 73 Z" fill="#F47920" stroke="#fff" stroke-width="6" stroke-linejoin="round"/></svg>`;

async function makeAsset(page, kind, dir, spec = {}) {
  const f = path.join(dir, `ov_${kind}_${spec.w || ''}_${spec.h || ''}_${spec.i ?? ''}.png`);
  let html = '';
  if (kind === 'arrow') html = arrowSvg;
  else if (kind === 'ring') html = `<div style="width:${RING}px;height:${RING}px;border-radius:50%;border:9px solid #F47920;box-shadow:0 0 0 5px rgba(255,255,255,.85),0 0 24px rgba(244,121,32,.7);box-sizing:border-box"></div>`;
  else if (kind === 'box') html = `<div style="width:${spec.w + 12}px;height:${spec.h + 12}px;border-radius:14px;border:8px solid #F47920;box-shadow:0 0 0 4px rgba(255,255,255,.85),0 0 22px rgba(244,121,32,.6);box-sizing:border-box"></div>`;
  else if (kind === 'label') html = `<div style="display:inline-block;font:700 36px Inter,sans-serif;background:#00437A;color:#fff;padding:14px 26px;border-radius:14px;box-shadow:0 6px 18px rgba(0,0,0,.3);white-space:nowrap;border-left:10px solid #F47920">${esc(spec.text)}</div>`;
  await page.setContent(`<html><body style="margin:0;background:transparent"><div id="a" style="display:inline-block">${html}</div></body></html>`);
  const el = await page.$('#a');
  await el.screenshot({ path: f, omitBackground: true });
  return f;
}
module.exports = { slideHtml, shotRect, makeAsset, ARROW, RING };
