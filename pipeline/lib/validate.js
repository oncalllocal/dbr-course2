// Lesson schema validation. Returns {errors:[], warnings:[]}; never throws.
const TYPES = ['title', 'bullets', 'stat', 'cols', 'quote', 'shot', 'clip'];

function validateLesson(lesson, { fileExists = () => true } = {}) {
  const errors = [], warnings = [];
  const e = (i, m) => errors.push(`slide ${i}: ${m}`);
  if (!lesson || typeof lesson !== 'object') return { errors: ['lesson is not an object'], warnings };
  if (!/^\d+\.\d+$/.test(String(lesson.id || ''))) errors.push(`id "${lesson.id}" must look like "2.3"`);
  if (!lesson.title) errors.push('missing title');
  if (!Array.isArray(lesson.slides) || !lesson.slides.length) { errors.push('slides must be a non-empty array'); return { errors, warnings }; }
  lesson.slides.forEach((s, i) => {
    if (!s || typeof s !== 'object') return e(i, 'slide is not an object');
    if (!TYPES.includes(s.type)) return e(i, `unknown type "${s.type}"`);
    if (!s.narration || !String(s.narration).trim()) e(i, 'empty narration');
    else {
      if (/\{\{|\}\}|\[[A-Z ]{3,}\]|<[A-Za-z ]{3,}>|\bTODO\b/.test(s.narration)) e(i, 'narration contains an unresolved placeholder (it would be spoken aloud)');
      if (/https?:|www\.|\.com\b|fp_ref|ocl-?marketing|main-page|\.(?:net|org|io|co)\b/i.test(s.narration)) e(i, 'narration contains a URL or the affiliate link (links belong on screen only)');
      // tag names such as dbr-dead-lead or elig-sms are rewritten by spoken() (hyphenated-tag rules), so they are not flagged\n      if (/\b(?:[Dd]br|[Dd]nc|[Ss]ms|[Gg]hl)\b/.test(s.narration.replace(/\bDBR\b|\bSMS\b|\bGHL\b|\bDNC\b/g, '').replace(/\b(?:dbr|elig|src|go|done|call|import)-[a-z0-9-]+\b/g, '').replace(/\b[a-z]+-(?:dbr|dnc|sms)\b/g, ''))) warnings.push(`slide ${i}: lower/Title-case acronym in narration; spoken() is case-sensitive`);
      const w = s.narration.trim().split(/\s+/).length;
      if (w > 150) e(i, `narration is ${w} words (>150); split the slide`); else if (w > 120) warnings.push(`slide ${i}: narration is ${w} words (>120); consider splitting`);
    }
    if (s.type === 'title' && !s.title) e(i, 'title slide needs title');
    if (s.type === 'bullets') { if (!s.title) e(i, 'bullets need title'); if (!Array.isArray(s.items) || !s.items.length) e(i, 'bullets need items'); else if (s.items.length > 5) warnings.push(`slide ${i}: ${s.items.length} bullets may overflow`); }
    if (s.type === 'stat' && (!s.big || !s.label)) e(i, 'stat needs big and label');
    if (s.type === 'cols') { if (!Array.isArray(s.cards) || s.cards.length < 2 || s.cards.length > 3) e(i, 'cols needs 2-3 cards'); else if (s.cards.some(c => !c.h || !c.p)) e(i, 'each card needs h and p'); }
    if (s.type === 'quote' && !s.text) e(i, 'quote needs text');
    if (s.type === 'clip') { if (!s.clip) e(i, 'clip needs a clip file (mp4, relative to lessons/)'); else if (/\.\./.test(s.clip)) e(i, 'clip path must not contain ..'); else if (!fileExists(s.clip)) warnings.push(`slide ${i}: clip file ${s.clip} not found`); }
    if (s.type === 'shot') {
      if (!s.image) e(i, 'shot needs image'); else if (/\.\./.test(s.image)) e(i, 'image path must not contain ..'); else if (!fileExists(s.image)) warnings.push(`slide ${i}: image "${s.image}" not found (placeholder will be rendered)`);
      if (!s.capture) e(i, 'shot needs capture (what to screenshot)');
      const ps = s.pointer == null ? [] : [].concat(s.pointer);
      ps.forEach((p, k) => {
        if (!p || typeof p !== 'object') return e(i, `pointer ${k} is not an object`);
        if (typeof p.x !== 'number' || typeof p.y !== 'number' || !(p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1)) e(i, `pointer ${k} x/y must be numbers in 0..1`);
        if (p.box) {
          if (!(p.box.w > 0 && p.box.w <= 1 && p.box.h > 0 && p.box.h <= 1)) e(i, `pointer ${k} box w/h must be 0..1`);
          else if (p.x - p.box.w / 2 < -0.001 || p.x + p.box.w / 2 > 1.001 || p.y - p.box.h / 2 < -0.001 || p.y + p.box.h / 2 > 1.001) warnings.push(`slide ${i}: pointer ${k} box extends past the image edge`);
        }
      });
    }
  });
  return { errors, warnings };
}
module.exports = { validateLesson, TYPES };
