// Pointer timeline math + ffmpeg overlay filtergraph for animated arrows, rings, boxes and labels.
const FLY = 1.1; // seconds for the arrow to travel between targets

/** Absolute pixel position of an image-relative point, given the displayed image rect. */
const toPx = (rect, p) => ({ x: rect.x + p.x * rect.w, y: rect.y + p.y * rect.h });

/** Schedule pointers across a slide of duration d. Explicit p.at (seconds) wins. */
function schedule(pointers, d) {
  const n = pointers.length; if (!n) return [];
  const first = Math.min(1.0, Math.max(0.3, d * 0.15));
  const last = Math.max(first, d - FLY - 1.2);
  return pointers.map((p, i) => ({ ...p, ts: p.at != null ? p.at : n === 1 ? first : first + (last - first) * i / (n - 1) }));
}

/** Build the overlay chain. inputs: base video is [0:v]; overlay PNG inputs start at index 2 (1 is audio). */
function buildFilter(rect, pointers, d, dims) {
  const sched = schedule(pointers, d); if (!sched.length) return { script: 'null', extraInputs: [] };
  const extra = [], lines = []; let cur = '0:v', idx = 2, k = 0;
  const add = (file, expr) => { extra.push(file); const out = `v${k++}`; lines.push(`[${cur}][${idx}:v]overlay=${expr}[${out}]`); cur = out; idx++; };
  let prev = null;
  sched.forEach((p, i) => {
    const c = toPx(rect, p), te = i + 1 < sched.length ? sched[i + 1].ts : d + 1;
    const start = prev || { x: Math.min(rect.x + rect.w - 40, c.x + 280), y: Math.min(rect.y + rect.h - 40, c.y + 190) };
    const s = `clip((t-${p.ts.toFixed(3)})/${FLY},0,1)`, e = `(${s}*${s}*(3-2*${s}))`;
    const ax = `${(start.x - dims.tipX).toFixed(1)}+${(c.x - start.x).toFixed(1)}*${e}`, ay = `${(start.y - dims.tipY).toFixed(1)}+${(c.y - start.y).toFixed(1)}*${e}`;
    const win = `between(t,${p.ts.toFixed(3)},${te.toFixed(3)})`;
    add('arrow', `x='${ax}':y='${ay}':enable='${win}'`);
    const land = (p.ts + FLY).toFixed(3);
    if (p.box) {
      const bw = Math.round(p.box.w * rect.w), bh = Math.round(p.box.h * rect.h);
      add(`box:${bw}:${bh}`, `x=${Math.round(c.x - bw / 2 - 6)}:y=${Math.round(c.y - bh / 2 - 6)}:enable='between(t,${land},${te.toFixed(3)})*lt(mod(t,1.4),1.0)'`);
    } else add('ring', `x=${Math.round(c.x - dims.ring / 2)}:y=${Math.round(c.y - dims.ring / 2)}:enable='between(t,${land},${te.toFixed(3)})*lt(mod(t,1.2),0.8)'`);
    if (p.label) {
      const right = c.x < rect.x + rect.w * 0.6;
      add(`label:${i}`, `x=${right ? Math.round(c.x + 84) : `${Math.round(c.x - 84)}-w`}:y=${Math.round(c.y + 4)}:enable='between(t,${(p.ts + 0.5).toFixed(3)},${te.toFixed(3)})'`);
    }
    prev = c;
  });
  lines[lines.length - 1] = lines[lines.length - 1].replace(/\[v\d+\]$/, '[vout]');
  return { script: lines.join(';\n'), extraInputs: extra };
}
module.exports = { schedule, buildFilter, toPx, FLY };
