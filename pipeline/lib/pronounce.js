// Spoken-form fixes applied to TTS text only (captions keep the original text).
const MAP = [
  // IDs first so the bare-acronym rules below do not split them
  [/\bWF-0?(\d+)\b/g, 'workflow $1'], [/\bREF-0?(\d+)\b/g, 'reference $1'], [/\bSOP-0?(\d+)\b/g, 'S O P $1'],
  [/\bGoHighLevel\b/g, 'Go High Level'], [/\bGHL\b/g, 'Go High Level'],
  [/\bDBR\b/g, 'D B R'], [/\bMCTB\b/g, 'missed call text back'], [/\bAI\b/g, 'A I'], [/\bCSR\b/g, 'C S R'], [/\bSMS\b/g, 'S M S'], [/\bA2P\b/g, 'A 2 P'], [/\b10DLC\b/g, '10 D L C'],
  [/\bCSV\b/g, 'C S V'], [/\bSPF\b/g, 'S P F'], [/\bDKIM\b/g, 'dee kim'], [/\bDMARC\b/g, 'dee mark'],
  [/\bDNC\b/g, 'D N C'], [/\bDND\b/g, 'D N D'], [/\bTCPA\b/g, 'T C P A'], [/\bCAN-SPAM\b/g, 'CAN SPAM'],
  [/\bSOPs?\b/g, m => (m.endsWith('s') ? 'S O Ps' : 'S O P')], [/\bCRM\b/g, 'C R M'], [/\bURL\b/g, 'U R L'],
  [/\bSaaS\b/g, 'sass'], [/\bAPI\b/g, 'A P I'], [/\bROI\b/g, 'R O I'], [/\bCTA\b/g, 'C T A'],
  [/\bE\.164\b/g, 'E 164'], [/\bHVAC\b/g, 'H V A C'], [/\bUTF-8\b/g, 'U T F 8'], [/\bN\/A\b/g, 'N slash A'], [/&/g, ' and '],
  [/\bHighLevel\b/g, 'High Level'], [/\bEIN\b/g, 'E I N'], [/\bIRS\b/g, 'I R S'], [/\bDNS\b/g, 'D N S'], [/\bMX\b/g, 'M X'], [/\bIP\b/g, 'I P'], [/\bID\b/g, 'I D'], [/\bPDF\b/g, 'P D F'], [/\bUS\b/g, 'U S'], [/\bDMs\b/g, 'D Ms'], [/\bDM\b/g, 'D M'], [/\bOK\b/g, 'okay'], [/\bmail-tester\b/gi, 'mail tester'], [/\s*—\s*/g, ', '],
];
// ---- PROPOSED additions to pipeline/lib/pronounce.js (append, then call from spoken()) ----
const DW = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine'];
const ONES = 'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split(' ');
const TENS = 'x x twenty thirty forty fifty sixty seventy eighty ninety'.split(' ');
function words(n) {            // 0 .. 999,999 in plain English ("1,800" -> "one thousand eight hundred")
  n = Number(n);
  if (n < 20) return ONES[n];
  if (n < 100) return TENS[Math.floor(n / 10)] + (n % 10 ? ' ' + ONES[n % 10] : '');
  if (n < 1000) return ONES[Math.floor(n / 100)] + ' hundred' + (n % 100 ? ' ' + words(n % 100) : '');
  if (n < 1e6) return words(Math.floor(n / 1000)) + ' thousand' + (n % 1000 ? ' ' + words(n % 1000) : '');
  return String(n);
}
const ampm = a => (a.toLowerCase() === 'a' ? ' A M' : ' P M');
const MAP2 = [
  // message and document IDs
  [/\bO-S(\d)\b/g, (m, d) => `O S ${DW[d]}`], [/\b([DPC])-S(\d)\b/g, (m, l, d) => `${l} S ${DW[d]}`], [/\bE-([DPC])(\d)\b/g, (m, l, d) => `email ${l} ${DW[d]}`],
  [/\bTPL-0?(\d+)\b/g, (m, d) => 'template ' + words(d)], [/\bCP-575\b/g, 'C P five seventy five'], [/\bT-(\d+)\b/g, (m, d) => 'test ' + words(d)],
  // tag names: hyphens become spaces, prefixes get a spoken form
  [/\b(dbr|elig|src)-([a-z0-9-]+)\b/g, (m, p, r) => ({ dbr: 'D B R', elig: 'eligible', src: 'source' })[p] + ' ' + r.replace(/-/g, ' ')],
  [/\b(go|done|call)-([a-z0-9-]+)\b/g, (m, p, r) => p + ' ' + r.replace(/-/g, ' ')],
  // lower-case / Title-case acronyms the case-sensitive map misses
  [/\b[Dd]br\b/g, 'D B R'], [/\b[Dd]nc\b/g, 'D N C'], [/\b[Dd]nd\b/g, 'D N D'], [/\b[Ss]ms\b/g, 'S M S'], [/\b[Cc]sv\b/g, 'C S V'], [/\b[Gg]hl\b/g, 'Go High Level'],
  [/\bElig\b/g, 'Eligible'], [/\belig\b/g, 'eligible'], [/\boptout\b/g, 'opt out'], [/\boptin\b/g, 'opt in'], [/\bMicrosoft 365\b/g, 'Microsoft three sixty five'],
  // acronyms found in the lessons that the map misses
  [/\bv=DMARC1;?/g, 'v equals dee mark one'], [/\bp=none;?/g, 'p equals none'], [/\bDMARC1\b/g, 'dee mark one'], [/\bTXT\b/g, 'T X T'], [/\bCNAME\b/g, 'C name'], [/\bSMTP\b/g, 'S M T P'],
  [/\bMXToolbox\b/g, 'M X Toolbox'], [/\bAT and T\b/g, 'A T and T'], [/\bIDs\b/g, 'I Ds'], [/\bURLs\b/g, 'U R Ls'], [/\bCSVs\b/g, 'C S Vs'],
  // punctuation
  [/\s*–\s*/g, ', '], [/\s*·\s*/g, ', '], [/\be\.g\./g, 'for example'], [/\bi\.e\./g, 'that is'], [/\bvs\./g, 'versus'], [/\betc\./g, 'and so on'], [/\s+([.,;:!?])/g, '$1'],
  // numbers
  [/\b([Ll]essons?) (\d+)\.(\d+)\b/g, (m, w, a, b) => `${w} ${words(a)} point ${words(b)}`], [/\b([Mm]odules?) (\d+)\b/g, (m, w, a) => `${w} ${words(a)}`],
  [/\$(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d\d))?/g, (m, d, c) => words(d.replace(/,/g, '')) + ' dollars' + (c ? ' ' + words(c) : '')],
  [/\b(\d+(?:\.\d+)?)\s?%/g, (m, d) => (d.includes('.') ? d.replace('.', ' point ') : words(d)) + ' percent'],
  [/\b(\d{1,2}):00\s?([AaPp])\.?[Mm]\.?/g, (m, h, a) => words(h) + ampm(a)], [/\b(\d{1,2})\s?([AaPp])\.?[Mm]\b\.?/g, (m, h, a) => words(h) + ampm(a)],
  [/(?<![\w.])(19|20)(\d\d)(?![\w.])/g, (m, a, b) => words(a) + ' ' + (b[0] === '0' && b[1] !== '0' ? 'oh ' + words(b[1]) : b === '00' ? 'hundred' : words(b))],
  [/(?<![\w.])(\d{1,3}(?:,\d{3})+|\d{1,6})(?!\w|\.\d)/g, (m, d) => words(d.replace(/,/g, ''))],
];
// in spoken(): return MAP2.reduce((t, [re, to]) => t.replace(re, to), <result of the existing MAP>).replace(/\s+/g, ' ').trim();

function spoken(text) {
  const first = MAP.reduce((t, [re, to]) => t.replace(re, to), text);
  return MAP2.reduce((t, [re, to]) => t.replace(re, to), first).replace(/\s+/g, ' ').trim();
}

// ---- Caption form: lessons are written in spoken form ("S O P zero eight"); captions should read like text. ----
// spoken() is untouched (voice cache key unchanged). captionText() never feeds the voice.
const NUM = { zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19, twenty: 20, thirty: 30, forty: 40, fifty: 50, sixty: 60, seventy: 70, eighty: 80, ninety: 90 };
const NW = Object.keys(NUM).join('|');
function wordsToNumber(phrase) {   // "one thousand eight hundred" -> 1800; null when not a plain number phrase
  let total = 0, cur = 0;
  for (const w of phrase.toLowerCase().split(/[\s-]+/)) {
    if (w in NUM) cur += NUM[w];
    else if (w === 'hundred') cur = (cur || 1) * 100;
    else if (w === 'thousand') { total += (cur || 1) * 1000; cur = 0; }
    else return null;
  }
  return total + cur;
}
const pad2 = w => String(NUM[w.toLowerCase()]).padStart(2, '0');
const NUMPH = `(?:${NW})(?:[\\s-]+(?:${NW}|hundred|thousand))*|(?:${NW}\\s+)?(?:hundred|thousand)(?:\\s+(?:${NW}|hundred|thousand))*`;
const CAP = [
  [/\bS R C dash D B R dash import\b/g, 'src-dbr-import'],
  [/\bA T X T\b/g, 'A TXT'], [/\bA C name\b/g, 'A CNAME'], [/\bA T and T\b/g, 'AT&T'],
  [/\bS O P (zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen)(?: (zero|one|two|three|four|five|six|seven|eight|nine))?\b/g, (m, a, b) => 'SOP-' + (b ? String(NUM[a] * 10 + NUM[b]).padStart(2, '0') : pad2(a))],
  [/\bS O Ps\b/g, 'SOPs'], [/\bS O P\b/g, 'SOP'], [/\bD B R S M S\b/g, 'DBR SMS'], [/\bC name\b/g, 'CNAME'],
  [/\bW F (zero|one|two|three|four|five|six|seven|eight|nine) (zero|one|two|three|four|five|six|seven|eight|nine)\b/g, (m, a, b) => 'WF-' + NUM[a] + NUM[b]],
  [/\bR E F (zero|one|two|three|four|five|six|seven|eight|nine) (zero|one|two|three|four|five|six|seven|eight|nine)\b/g, (m, a, b) => 'REF-' + NUM[a] + NUM[b]],
  [/\bR E F (one|two|three|four|five|six|seven|eight|nine)\b/g, (m, a) => 'REF-0' + NUM[a]],
  [/\b([OPCD]) S (zero|one|two|three|four|five|six|seven|eight|nine)\b/g, (m, l, d) => `${l}-S${NUM[d]}`],
  [/\bten D L C\b/g, '10DLC'], [/\bA 2 P\b/g, 'A2P'],
  [/\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve) ([AP]) M\b/g, (m, h, a) => `${NUM[h]} ${a}M`],
  [new RegExp(`\\b(${NUMPH})\\s+to\\s+(${NUMPH})\\s+dollars\\b`, 'gi'), (m, x, y) => { const a = wordsToNumber(x), b = wordsToNumber(y); return a === null || b === null ? m : `$${a} to $${b}`; }],
  [new RegExp(`\\b(${NUMPH})\\s+dollars\\b`, 'gi'), (m, n) => { const v = wordsToNumber(n); return v === null ? m : '$' + v.toLocaleString('en-US'); }],
  [new RegExp(`\\b(${NUMPH})(?:\\s+point\\s+((?:${NW})(?:\\s+(?:${NW}))*))?\\s+percent\\b`, 'gi'), (m, n, f) => { const v = wordsToNumber(n); if (v === null) return m; const fr = f ? f.split(/\s+/).map(w => NUM[w.toLowerCase()]).join('') : ''; return v + (fr ? '.' + fr : '') + '%'; }],
  // any remaining run of 2+ spaced capital letters (D B R, E I N, M X, T X T, I D ...) collapses; a leading article "A" stays apart
  [/\b(A )?((?:[A-Z] ){1,}[A-Z])\b(?!['\w-])/g, (m, art, run) => { const l = run.replace(/ /g, ''); if (/^[ABC]{2,3}$/.test(l) && !art) return m; return (art || '') + l; }],
];
function captionText(text) {
  return CAP.reduce((t, [re, to]) => t.replace(re, to), String(text)).replace(/\*/g, '').trim();
}
module.exports = { spoken, captionText };
