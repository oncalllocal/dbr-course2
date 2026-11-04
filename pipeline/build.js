#!/usr/bin/env node
/**
 * Missed-call-text-back course and video renderer.
 *   node build.js lessons/1.1.json [more.json ...]   render lessons -> out/<id>.mp4 + .srt
 *   node build.js --all                              render every lessons/*.json
 *   node build.js --stats                            validate everything + TTS character/cost estimate (no render)
 * Flags: --strict  fail if any shot image is missing | --silent  ignore ELEVENLABS_API_KEY | --lessons-dir <dir>
 * Env: ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL, MCE_OUT (output folder, default out/)
 */
const fs = require('fs'), path = require('path'), cp = require('child_process');
// Node's built-in fetch ignores HTTPS_PROXY unless NODE_USE_ENV_PROXY=1; re-exec once so API calls work behind the sandbox proxy.
if ((process.env.HTTPS_PROXY || process.env.https_proxy) && !process.env.NODE_USE_ENV_PROXY) {
  const r = cp.spawnSync(process.execPath, [__filename, ...process.argv.slice(2)], { stdio: 'inherit', env: { ...process.env, NODE_USE_ENV_PROXY: '1', NODE_NO_WARNINGS: '1' } });
  process.exit(r.status === null ? 1 : r.status);
}
const { chromium } = require('playwright');
const { validateLesson } = require('./lib/validate');
const tts = require('./lib/tts');
const { captionText } = require('./lib/pronounce');
const { slideHtml, shotRect, makeAsset, ARROW, RING } = require('./lib/slides');
const { buildFilter } = require('./lib/pointer');

const root = process.env.MCE_ROOT ? path.resolve(process.env.MCE_ROOT) : path.resolve(__dirname, '..');
const args = process.argv.slice(2), flag = f => args.includes(f);
if (flag('--silent')) process.env.MCE_SILENT = '1';
const lessonsDir = path.resolve(root, args.includes('--lessons-dir') ? args[args.indexOf('--lessons-dir') + 1] : 'lessons');
const outDir = process.env.MCE_OUT ? path.resolve(process.env.MCE_OUT) : path.join(root, 'out'); fs.mkdirSync(outDir, { recursive: true }); // MCE_OUT: render somewhere else (for example review copies) without touching out/
const run = c => cp.execSync(c, { stdio: ['ignore', 'pipe', 'pipe'] }).toString();
const dur = f => parseFloat(run(`ffprobe -v error -show_entries format=duration -of csv=p=0 "${f}"`));
const stamp = t => { const h = Math.floor(t / 3600), m = Math.floor(t % 3600 / 60), s = (t % 60).toFixed(3).padStart(6, '0').replace('.', ','); return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${s}`; };
const sortLessons = a => a.sort((x, y) => x.split('/').pop().localeCompare(y.split('/').pop(), undefined, { numeric: true }));

// Fill {{KEYS}} from course.config.json into on-screen text (never narration/capture). Returns the set of keys left unfilled.
const config = (() => { try { return JSON.parse(fs.readFileSync(path.join(root, 'course.config.json'), 'utf8')); } catch { return {}; } })();
function fillPlaceholders(node, key = '', left = new Set()) {
  if (typeof node === 'string') return node.replace(/\{\{([A-Z_]+)\}\}/g, (m, k) => { if (config[k]) return config[k]; left.add(m); return m; });
  if (Array.isArray(node)) { node.forEach((v, i) => { node[i] = fillPlaceholders(v, key, left); }); return node; }
  if (node && typeof node === 'object') { for (const k of Object.keys(node)) { if (k === 'narration' || k === 'capture' || k === 'placeholders' || k === 'notes') continue; node[k] = fillPlaceholders(node[k], k, left); } return node; }
  return node;
}
function loadLesson(file) {
  let lesson; try { lesson = JSON.parse(fs.readFileSync(file, 'utf8')); } catch (e) { return { file, error: `invalid JSON: ${e.message}` }; }
  const resolve = img => path.resolve(lessonsDir, img);
  const v = validateLesson(lesson, { fileExists: img => fs.existsSync(resolve(img)) });
  const unresolved = new Set(); fillPlaceholders(lesson, '', unresolved);
  if (unresolved.size) v.warnings.push(`unresolved on-screen placeholder(s): ${[...unresolved].join(', ')} (set in course.config.json)`);
  return { file, lesson, ...v, resolve, unresolved };
}

async function render(item, browser) {
  const { lesson, resolve } = item, id = lesson.id;
  const outName = lesson.out || id; const work = path.join(outDir, 'work_' + outName); fs.rmSync(work, { recursive: true, force: true }); fs.mkdirSync(work, { recursive: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  const segs = [], durs = [], trans = []; const XF = 0.45;   // crossfade length; each segment starts with XF of silence so the dissolve never clips a word
  let srt = '', t = 0, voiced = 0, chars = 0, missing = [];
  for (let i = 0; i < lesson.slides.length; i++) {
    const s = lesson.slides[i], n = String(i).padStart(2, '0');
    const imgPath = s.type === 'shot' && fs.existsSync(resolve(s.image)) ? resolve(s.image) : null;
    if (s.type === 'shot' && !imgPath) missing.push(s.image);
    await page.setContent(slideHtml(lesson, s, imgPath)); await page.evaluate(() => document.fonts.ready); await page.waitForTimeout(120);
    await page.screenshot({ path: `${work}/s${n}.png` });
    const wav = `${work}/a${n}.wav`;
    if (tts.enabled()) {
      let r = null;
      try { r = await tts.synth(s.narration, path.join(outDir, 'tts-cache')); }
      catch (e) {
        // No usable credentials / host blocked on the very first call -> degrade to silent instead of failing the run.
        if (voiced === 0 && !tts.hasEnvKey() && (e.status === 401 || e.status === 403 || !e.status)) { console.warn(`! voice unavailable (${e.message.slice(0, 120)}); rendering silent. Add the ElevenLabs secret or ELEVENLABS_API_KEY.`); process.env.MCE_SILENT = '1'; }
        else throw e;
      }
      if (r) { chars += r.chars; voiced++; run(`ffmpeg -y -loglevel error -i "${r.file}" -ar 44100 -ac 2 -af "silenceremove=start_periods=1:start_threshold=-50dB" "${wav}"`); }
    }
    if (!fs.existsSync(wav)) { const d = Math.max(3, s.narration.trim().split(/\s+/).length / 2.5); run(`ffmpeg -y -loglevel error -f lavfi -i anullsrc=r=44100:cl=stereo -t ${d.toFixed(2)} "${wav}"`); }
    const clipFile = s.type === 'clip' ? resolve(s.clip) : null;
    const d = Math.max(dur(wav) + 0.6 + XF, clipFile && fs.existsSync(clipFile) ? dur(clipFile) : 0), seg = `${work}/seg${n}.mp4`;
    durs.push(d); trans.push(s.transition || 'fade');
    let filter = '[0:v]null[vout]', extra = '';
    if (s.type === 'shot' && s.pointer) {
      const rect = await shotRect(page), ps = [].concat(s.pointer);
      const built = buildFilter(rect, ps, d, { tipX: ARROW.tipX, tipY: ARROW.tipY, ring: RING });
      const files = [];
      for (const spec of built.extraInputs) {
        const [kind, a, b] = spec.split(':');
        files.push(await makeAsset(page, kind, work, kind === 'box' ? { w: +a, h: +b } : kind === 'label' ? { i: +a, text: ps[+a].label } : {}));
      }
      fs.writeFileSync(`${work}/f${n}.txt`, built.script);
      filter = `-filter_complex_script ${work}/f${n}.txt -map "[vout]" -map 1:a`;
      extra = files.map(f => `-loop 1 -t ${d.toFixed(2)} -i "${f}"`).join(' ');
    }
    if (clipFile && fs.existsSync(clipFile)) {
      run(`ffmpeg -y -loglevel error -i "${clipFile}" -i "${wav}" -filter_complex "[0:v]scale=1920:1080,tpad=stop_mode=clone:stop_duration=${d.toFixed(2)},fps=30,format=yuv420p[vout]" -map "[vout]" -map 1:a -af "adelay=${XF * 1000}|${XF * 1000},apad=pad_dur=${d.toFixed(2)}" -t ${d.toFixed(2)} -c:v libx264 -preset medium -crf 20 -r 30 -c:a aac -b:a 160k "${seg}"`);
      segs.push(`file 'seg${n}.mp4'`); srt += `${i + 1}\n${stamp(t)} --> ${stamp(t + d - 0.5)}\n${captionText(s.caption || s.narration)}\n\n`; t += d - XF; continue;
    }
    const maps = filter.startsWith('-filter') ? filter : `-filter_complex "${filter}" -map "[vout]" -map 1:a`;
    run(`ffmpeg -y -loglevel error -loop 1 -t ${d.toFixed(2)} -i ${work}/s${n}.png -i "${wav}" ${extra} ${maps} -af "adelay=${XF * 1000}|${XF * 1000},apad=pad_dur=0.6" -t ${d.toFixed(2)} -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -r 30 -c:a aac -b:a 160k "${seg}"`);
    segs.push(`file 'seg${n}.mp4'`);
    srt += `${i + 1}\n${stamp(t)} --> ${stamp(t + d - 0.5)}\n${captionText(s.caption || s.narration)}\n\n`; t += d - XF;
  }
  await page.close();
  const base = path.join(outDir, outName); fs.writeFileSync(base + '.srt', srt);
  const n = segs.length; const ins = segs.map((_, i) => `-i ${work}/seg${String(i).padStart(2, '0')}.mp4`).join(' ');
  let vf = '', af = '', vlast = '[0:v]', alast = '[0:a]', acc = 0;
  for (let i = 1; i < n; i++) {
    acc += durs[i - 1]; const off = (acc - i * XF).toFixed(3), vo = i === n - 1 ? 'vout' : `v${i}`, ao = i === n - 1 ? 'aout' : `a${i}`;
    vf += `${vlast}[${i}:v]xfade=transition=${trans[i]}:duration=${XF}:offset=${off}[${vo}];`; af += `${alast}[${i}:a]acrossfade=d=${XF}[${ao}];`; vlast = `[${vo}]`; alast = `[${ao}]`;
  }
  const graph = (n > 1 ? (vf + af).replace(/;$/, '') : '[0:v]null[vout];[0:a]anull[aout]') + ';[aout]loudnorm=I=-16:TP=-1.5:LRA=11[aoutn]';
  fs.writeFileSync(`${work}/graph.txt`, graph);
  run(`ffmpeg -y -loglevel error ${ins} -i ${base}.srt -filter_complex_script ${work}/graph.txt -map "[vout]" -map "[aoutn]" -map ${n}:s -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -ar 44100 -c:a aac -b:a 160k -c:s mov_text -metadata:s:s:0 language=eng ${base}.mp4`);
  return { id, seconds: t, voiced: voiced > 0, chars, missing };
}

(async () => {
  let files = args.filter(a => a.endsWith('.json')).map(a => path.resolve(a));
  if (flag('--all') || flag('--stats')) files = sortLessons(fs.readdirSync(lessonsDir).filter(f => /^\d+\.\d+\.json$/.test(f)).map(f => path.join(lessonsDir, f)));
  if (!files.length) { console.error('usage: build.js <lesson.json...> | --all | --stats'); process.exit(2); }
  const items = files.map(loadLesson); let bad = 0;
  for (const it of items) {
    const name = path.basename(it.file);
    if (it.error) { console.error(`✗ ${name}: ${it.error}`); bad++; continue; }
    it.errors.forEach(m => console.error(`✗ ${name} ${m}`)); it.warnings.forEach(m => console.warn(`! ${name} ${m}`)); if (it.errors.length) bad++;
  }
  if (flag('--stats')) {
    let chars = 0, words = 0, shots = 0, missing = 0, slides = 0;
    for (const it of items.filter(i => i.lesson && !i.errors.length)) for (const s of it.lesson.slides) { slides++; chars += s.narration.length; words += s.narration.trim().split(/\s+/).length; if (s.type === 'shot') { shots++; if (!fs.existsSync(it.resolve(s.image))) missing++; } }
    console.log(`lessons=${items.length} slides=${slides} narration: ${words} words, ${chars} chars (~${(words / 150).toFixed(0)} min)  shots=${shots} (missing images: ${missing})  invalid=${bad}`);
    process.exit(bad ? 1 : 0);
  }
  if (bad) { console.error(`${bad} lesson(s) failed validation; nothing rendered.`); process.exit(1); }
  console.log(tts.enabled() ? `voice: ElevenLabs (${process.env.ELEVENLABS_VOICE_ID || 'default voice'}; key via ${tts.hasEnvKey() ? 'env' : 'sandbox secret proxy'})` : 'voice: SILENT (MCE_SILENT set)');
  const browser = await chromium.launch(); let failed = 0;
  try {
    for (const it of items) {
      try {
        const r = await render(it, browser);
        if (flag('--strict') && r.missing.length) throw new Error(`missing screenshots: ${r.missing.join(', ')}`);
        if (flag('--strict') && it.unresolved.size) throw new Error(`unresolved placeholders: ${[...it.unresolved].join(', ')}`);
        console.log(`✓ ${r.id}  ${r.seconds.toFixed(0)}s  ${r.voiced ? `voiced (${r.chars} new chars)` : 'silent'}${r.missing.length ? `  [${r.missing.length} screenshot placeholder(s)]` : ''}`);
      } catch (e) { failed++; console.error(`✗ ${it.lesson.id}: ${e.message}`); }
    }
  } finally { await browser.close(); }
  process.exit(failed ? 1 : 0);
})();
