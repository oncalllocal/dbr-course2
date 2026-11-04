// ElevenLabs text-to-speech with an on-disk cache (re-renders cost nothing) and retry/backoff.
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const { spoken } = require('./pronounce');
const MODEL = process.env.ELEVENLABS_MODEL || 'eleven_multilingual_v2';
const VOICE = () => process.env.ELEVENLABS_VOICE_ID || 'l4Coq6695JDX9xtLqXDE';
// The key may be an env var OR injected by the sandbox's network-secret proxy (header xi-api-key), in which case
// no env var exists. So voice is "enabled" unless silenced; build.js falls back to silent if the first call is rejected.
const enabled = () => !process.env.MCE_SILENT;
const hasEnvKey = () => !!process.env.ELEVENLABS_API_KEY;
const cacheKey = (text, voice = VOICE(), model = MODEL) => crypto.createHash('sha256').update(`${voice}|${model}|${spoken(text)}`).digest('hex').slice(0, 32);
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function synth(text, cacheDir, fetchImpl = fetch) {
  fs.mkdirSync(cacheDir, { recursive: true });
  const file = path.join(cacheDir, cacheKey(text) + '.mp3');
  if (fs.existsSync(file) && fs.statSync(file).size > 1000) return { file, cached: true, chars: 0 };
  const body = JSON.stringify({ text: spoken(text), model_id: MODEL, voice_settings: { stability: 0.5, similarity_boost: 0.75, style: 0.1, use_speaker_boost: true } });
  let lastErr;
  for (let attempt = 0; attempt < 5; attempt++) {
    const r = await fetchImpl(`https://api.elevenlabs.io/v1/text-to-speech/${VOICE()}?output_format=mp3_44100_128`, { method: 'POST', headers: { ...(hasEnvKey() ? { 'xi-api-key': process.env.ELEVENLABS_API_KEY } : {}), 'Content-Type': 'application/json' }, body });
    if (r.ok) { fs.writeFileSync(file, Buffer.from(await r.arrayBuffer())); return { file, cached: false, chars: text.length }; }
    const msg = await r.text(); lastErr = new Error(`ElevenLabs ${r.status}: ${msg.slice(0, 300)}`); lastErr.status = r.status;
    if (r.status === 401 || r.status === 403 || r.status === 422) throw lastErr; // not retryable
    await sleep(1000 * 2 ** attempt);
  }
  throw lastErr;
}
module.exports = { synth, enabled, hasEnvKey, cacheKey };
