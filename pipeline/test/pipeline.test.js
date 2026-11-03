const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('fs'), os = require('os'), path = require('path'), cp = require('child_process');
const { validateLesson } = require('../lib/validate');
const { spoken } = require('../lib/pronounce');
const { schedule, buildFilter, toPx } = require('../lib/pointer');
const tts = require('../lib/tts');

const ok = { id: '1.1', title: 'T', slides: [{ type: 'quote', text: 'x', narration: 'Hello there.' }] };

test('validate: accepts a minimal lesson', () => assert.deepEqual(validateLesson(ok).errors, []));
test('validate: rejects bad id, unknown type, empty narration', () => {
  const r = validateLesson({ id: 'x', title: 'T', slides: [{ type: 'nope', narration: 'a' }, { type: 'quote', text: 'q', narration: ' ' }] });
  assert.equal(r.errors.length, 3);
});
test('validate: placeholders in narration are errors (would be spoken)', () => {
  const r = validateLesson({ ...ok, slides: [{ type: 'quote', text: 'q', narration: 'Use {{AFFILIATE_LINK}} now' }] });
  assert.match(r.errors[0], /placeholder/);
});
test('validate: placeholders in on-screen text are allowed', () => {
  assert.deepEqual(validateLesson({ ...ok, slides: [{ type: 'quote', text: 'Go to {{AFFILIATE_LINK}}', narration: 'Use the link below.' }] }).errors, []);
});
test('validate: shot needs capture and pointer in 0..1; missing image is only a warning', () => {
  const bad = validateLesson({ ...ok, slides: [{ type: 'shot', image: 'a.png', pointer: { x: 2, y: 0.5 }, narration: 'n' }] });
  assert.equal(bad.errors.length, 2);
  const good = validateLesson({ ...ok, slides: [{ type: 'shot', image: 'a.png', capture: 'c', pointer: [{ x: 0.1, y: 0.2 }], narration: 'n' }] }, { fileExists: () => false });
  assert.deepEqual(good.errors, []); assert.equal(good.warnings.length, 1);
});
test('validate: null pointers/slides never throw; string coords rejected; URLs and affiliate link in narration are errors; >150 words is an error', () => {
  const base = { id: '1.1', title: 't', slides: [{ type: 'shot', image: 'shots/a.png', capture: 'x', narration: 'Hello there.', pointer: [null] }] };
  assert.ok(validateLesson(base).errors.some(m => /pointer 0 is not an object/.test(m)));
  assert.ok(validateLesson({ ...base, slides: [null] }).errors.some(m => /not an object/.test(m)));
  assert.ok(validateLesson({ ...base, slides: [{ ...base.slides[0], pointer: [{ x: '0.5', y: 0.5 }] }] }).errors.some(m => /numbers in 0..1/.test(m)));
  assert.ok(validateLesson({ ...base, slides: [{ ...base.slides[0], pointer: [], narration: 'Go to https://x.com/y?fp_ref=abc now.' }] }).errors.some(m => /URL or the affiliate/.test(m)));
  assert.ok(validateLesson({ ...base, slides: [{ ...base.slides[0], pointer: [], narration: 'word '.repeat(151) }] }).errors.some(m => /\(>150\)/.test(m)));
  assert.ok(validateLesson({ ...base, slides: [{ ...base.slides[0], pointer: [{ x: 0.02, y: 0.5, box: { w: 0.2, h: 0.1 } }] }] }).warnings.some(m => /past the image edge/.test(m)));
});
test('pronounce: IDs and acronyms are spoken, not spelled', () => {
  assert.equal(spoken('Open WF-12 and REF-04 then SOP-15.'), 'Open workflow twelve and reference four then S O P fifteen.');
  assert.equal(spoken('Your EIN, DNS and MX records, US only, OK.'), 'Your E I N, D N S and M X records, U S only, okay.');
  assert.equal(spoken('HighLevel and GoHighLevel'), 'High Level and Go High Level');
});
test('pronounce: spoken forms, captions untouched', () => {
  assert.equal(spoken('Set up GHL for DBR & SMS'), 'Set up Go High Level for D B R and S M S');
  assert.equal(spoken('A2P 10DLC'), 'A two P ten D L C');
});
test('pointer: schedule keeps explicit "at" and orders others within the slide', () => {
  const s = schedule([{ x: 0, y: 0 }, { x: 1, y: 1, at: 9 }, { x: 0.5, y: 0.5 }], 12);
  assert.equal(s[1].ts, 9); assert.ok(s[0].ts < s[2].ts);
});
test('pointer: toPx maps image-relative coords to slide pixels', () => assert.deepEqual(toPx({ x: 100, y: 50, w: 800, h: 400 }, { x: 0.5, y: 0.25 }), { x: 500, y: 150 }));
test('pointer: filter chain ends in [vout] and lists one input per overlay', () => {
  const f = buildFilter({ x: 60, y: 116, w: 1800, h: 830 }, [{ x: 0.2, y: 0.3, label: 'A' }, { x: 0.6, y: 0.6, box: { w: 0.2, h: 0.1 } }], 14, { tipX: 14, tipY: 12, ring: 120 });
  assert.equal(f.extraInputs.length, 5); // arrow,ring,label + arrow,box
  assert.match(f.script, /\[vout\]$/); assert.equal(f.script.split(';\n').length, 5);
});
test('pointer: no pointers -> passthrough', () => assert.equal(buildFilter({ x: 0, y: 0, w: 1, h: 1 }, [], 5, {}).script, 'null'));

test('tts: cache hit costs zero chars; miss calls API once; 401 is not retried', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'tts-')); process.env.ELEVENLABS_API_KEY = 'k';
  let calls = 0; const fake = async () => { calls++; return { ok: true, status: 200, arrayBuffer: async () => Buffer.alloc(2048, 1), text: async () => '' }; };
  const a = await tts.synth('Hello GHL', dir, fake), b = await tts.synth('Hello GHL', dir, fake);
  assert.equal(calls, 1); assert.equal(a.cached, false); assert.equal(b.cached, true); assert.equal(b.chars, 0);
  let n = 0; const denied = async () => { n++; return { ok: false, status: 401, text: async () => 'bad key' }; };
  await assert.rejects(tts.synth('other text', dir, denied), /401/); assert.equal(n, 1);
});
test('tts: cache key changes with voice', () => {
  const k1 = tts.cacheKey('hi', 'v1'), k2 = tts.cacheKey('hi', 'v2'); assert.notEqual(k1, k2);
});

test('integration: renders a 2-slide lesson with pointer + missing-shot placeholder', { timeout: 120000 }, () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'dbr-')); fs.mkdirSync(path.join(root, 'lessons'), { recursive: true }); fs.mkdirSync(path.join(root, 'brand'));
  fs.copyFileSync(path.join(__dirname, '../../brand/logo.png'), path.join(root, 'brand/logo.png'));
  fs.writeFileSync(path.join(root, 'lessons/9.1.json'), JSON.stringify({ id: '9.1', title: 'Test', slides: [
    { type: 'shot', image: 'shots/none.png', title: 'S', capture: 'a screen', pointer: [{ x: 0.5, y: 0.5, label: 'Here' }], narration: 'Click here to continue with the setup.' },
    { type: 'title', title: 'Done', narration: 'All done.' }] }));
  const out = cp.spawnSync('node', [path.join(__dirname, '../build.js'), path.join(root, 'lessons/9.1.json')], { env: { ...process.env, MCE_ROOT: root, MCE_SILENT: '1' }, encoding: 'utf8' });
  assert.equal(out.status, 0, out.stderr); assert.match(out.stdout, /✓ 9\.1/);
  const d = parseFloat(cp.execSync(`ffprobe -v error -show_entries format=duration -of csv=p=0 ${root}/out/9.1.mp4`).toString());
  assert.ok(d > 4 && d < 20); assert.ok(fs.readFileSync(path.join(root, 'out/9.1.srt'), 'utf8').includes('Click here'));
  const strict = cp.spawnSync('node', [path.join(__dirname, '../build.js'), '--strict', path.join(root, 'lessons/9.1.json')], { env: { ...process.env, MCE_ROOT: root, MCE_SILENT: '1' }, encoding: 'utf8' });
  assert.notEqual(strict.status, 0); // --strict fails on missing screenshots
});
test('integration: invalid lesson renders nothing and exits non-zero', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'dbr-')); fs.mkdirSync(path.join(root, 'lessons'));
  fs.writeFileSync(path.join(root, 'lessons/9.2.json'), JSON.stringify({ id: '9.2', title: 'x', slides: [{ type: 'quote', text: 'q', narration: '' }] }));
  const r = cp.spawnSync('node', [path.join(__dirname, '../build.js'), path.join(root, 'lessons/9.2.json')], { env: { ...process.env, MCE_ROOT: root }, encoding: 'utf8' });
  assert.equal(r.status, 1); assert.match(r.stderr, /empty narration/);
});

test('integration: {{PLACEHOLDERS}} are filled on-screen from course.config.json; --strict fails if one is unset', { timeout: 120000 }, () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'dbr-')); fs.mkdirSync(path.join(root, 'lessons')); fs.mkdirSync(path.join(root, 'brand'));
  fs.copyFileSync(path.join(__dirname, '../../brand/logo.png'), path.join(root, 'brand/logo.png'));
  fs.writeFileSync(path.join(root, 'course.config.json'), JSON.stringify({ A: 'https://x.test/a', B: '' }));
  fs.writeFileSync(path.join(root, 'lessons/9.3.json'), JSON.stringify({ id: '9.3', title: 'T', slides: [
    { type: 'bullets', title: 'Links', items: ['Go to {{A}}', 'Offer {{B}}'], narration: 'Use the link on screen.' }] }));
  const env = { ...process.env, MCE_ROOT: root, MCE_SILENT: '1' };
  const f = path.join(root, 'lessons/9.3.json');
  const loose = cp.spawnSync('node', [path.join(__dirname, '../build.js'), f], { env, encoding: 'utf8' });
  assert.equal(loose.status, 0, loose.stderr); assert.match(loose.stderr + loose.stdout, /unresolved on-screen placeholder.*\{\{B\}\}/);
  const strict = cp.spawnSync('node', [path.join(__dirname, '../build.js'), '--strict', f], { env, encoding: 'utf8' });
  assert.notEqual(strict.status, 0); assert.match(strict.stderr, /unresolved placeholders/);
});

// ---- captions: written/readable form, voice unchanged ----
test('captions keep written IDs while spoken() still spells them for the voice', () => {
  const { spoken, captionText } = require('../lib/pronounce');
  assert.equal(captionText('Open SOP-08 and WF-01 for A2P, the DBR plan.'), 'Open SOP-08 and WF-01 for A2P, the DBR plan.');
  assert.equal(spoken('SOP-08'), 'S O P eight');
  assert.equal(spoken('WF-01 runs first'), 'workflow one runs first');
  assert.equal(captionText('$1,800 at 9 AM'), '$1,800 at 9 AM');
});
test('captionText turns phonetic narration back into readable captions', () => {
  const { captionText } = require('../lib/pronounce');
  assert.equal(captionText('open S O P zero eight and W F zero one'), 'open SOP-08 and WF-01');
  assert.equal(captionText('the D B R, an A 2 P check, your E I N'), 'the DBR, an A2P check, your EIN');
  assert.equal(captionText('eighteen hundred dollars at nine A M, ten percent off'), '$1,800 at 9 AM, 10% off');
  assert.equal(captionText('a caption with *stars*'), 'a caption with stars');
});
test('spoken() output is unchanged (voice cache key stability)', () => {
  const { spoken } = require('../lib/pronounce');
  assert.equal(spoken('DBR and A2P with GHL'), 'D B R and A two P with Go High Level');
});
