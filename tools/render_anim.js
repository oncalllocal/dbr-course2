// Renders the before/after missed-call animation to mp4 (frame-exact, 30 fps, 1920x1080).
// node tools/render_anim.js <before|after> <out.mp4> [--biz "Name"] [--comp "Name"] [--job "a $12,000 repipe"] [--cust "..."] [--reply "..."]
const { chromium } = require('playwright'); const path = require('path'), fs = require('fs'), cp = require('child_process');
const [mode, out, ...rest] = process.argv.slice(2); const opt = {};
for (let i = 0; i < rest.length; i += 2) opt[rest[i].replace(/^--/, '')] = rest[i + 1];
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  const url = 'file://' + path.resolve(__dirname, 'anim/missed_call.html') + '?' + new URLSearchParams({ mode, ...opt });
  await p.goto(url); await p.evaluate(() => document.fonts.ready);
  const END = await p.evaluate(() => window.END), N = Math.round(END * 30), tmp = fs.mkdtempSync(path.join(require('os').tmpdir(), 'anim-'));
  const only = process.env.ANIM_FRAMES ? process.env.ANIM_FRAMES.split(',').map(Number) : null;   // debug: render only these times
  if (only) { for (const t of only) { await p.evaluate(t => window.renderAt(t), t); await p.screenshot({ path: path.resolve(out.replace(/\.mp4$/, '') + `_t${t}.png`) }); } await b.close(); return; }
  for (let i = 0; i < N; i++) { await p.evaluate(t => window.renderAt(t), i / 30); await p.screenshot({ path: path.join(tmp, String(i).padStart(5, '0') + '.jpg'), type: 'jpeg', quality: 92 }); }
  await b.close(); fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
  cp.execSync(`ffmpeg -y -loglevel error -framerate 30 -i ${tmp}/%05d.jpg -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p "${path.resolve(out)}"`);
  fs.rmSync(tmp, { recursive: true, force: true }); console.log('wrote', out, (N / 30).toFixed(1) + 's');
})().catch(e => { console.error(e.message); process.exit(1); });
