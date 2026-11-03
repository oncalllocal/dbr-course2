# Course video pipeline

Turns lesson JSON files into narrated MP4s (1080p, branded slides, animated arrow pointer on screenshot slides) plus `.srt` captions.

## Quick start

```bash
cd /home/user/missed-call-engine
node pipeline/build.js --stats            # validate every lesson + narration size/cost estimate
node pipeline/build.js lessons/1.1.json   # render one lesson -> out/1.1.mp4 + out/1.1.srt
node pipeline/build.js --all              # render everything
cd pipeline && npm test                   # run the test suite
```

No `ELEVENLABS_API_KEY` set → videos are silent placeholders with timing estimated from word count. With a key, audio is generated per slide, slide length follows the audio, and every clip is cached in `out/tts-cache/` (re-rendering costs zero characters unless the narration text, voice, or model changed).

| Env var | Purpose |
|---|---|
| `ELEVENLABS_API_KEY` | enables real voiceover |
| `ELEVENLABS_VOICE_ID` | voice to use (default: a stock voice) |
| `ELEVENLABS_MODEL` | default `eleven_multilingual_v2` |
| `MCE_SILENT=1` / `--silent` | force silent render even if a key exists |

Flags: `--strict` fails a lesson if any screenshot is missing (use for the final release render).

## Lesson file format (`lessons/<module>.<n>.json`)

```json
{ "id": "2.2", "title": "Create your sub-account", "slides": [ { "type": "...", "narration": "..." } ] }
```

Slide types: `title` (title, sub), `bullets` (title, items[]), `stat` (big, label), `cols` (title, cards[{h,p}]), `quote` (text), `shot`.
Wrap words in `*asterisks*` to highlight them in orange.

`shot` slide — a real screenshot with an animated pointer:

```json
{ "type": "shot", "image": "shots/2.2-create.png", "title": "Click Create Sub-Account",
  "capture": "Agency > Sub-Accounts page, with the Create Sub-Account button visible",
  "pointer": [ { "x": 0.82, "y": 0.12, "label": "Click here" },
               { "x": 0.5, "y": 0.5, "box": { "w": 0.3, "h": 0.1 }, "label": "Fill this in" } ],
  "narration": "..." }
```

- `x`,`y` are 0–1 positions **on the screenshot** (0,0 = top-left). `box` draws a highlight rectangle centered there. Optional `at` = seconds into the slide.
- Pointers appear in order across the narration, the arrow flying from one to the next.
- If the image file is missing, a striped **SCREENSHOT NEEDED** placeholder shows the `capture` text. `docs/SCREENSHOT_SHOT_LIST.md` lists every needed shot.
- Screenshots go in `lessons/shots/`, 16:9 PNG at 1600×900 or larger recommended.

## Narration rules (enforced by the validator)

- Never put `{{PLACEHOLDERS}}` or `[BRACKETS]` in narration (they would be spoken). On-screen text may contain them.
- Write for the ear: short sentences, ≤120 words per slide.
- `GHL`, `DBR`, `SMS`, `A2P`, `10DLC`, `CSV`, `DNC` etc. are auto-converted to spoken form for TTS (captions keep your text). Add more in `lib/pronounce.js`.

## Architecture

`build.js` (CLI) → `lib/validate.js` (schema) → `lib/slides.js` (HTML → PNG via Playwright, overlay assets) → `lib/tts.js` (ElevenLabs + cache) → `lib/pointer.js` (timeline + ffmpeg overlay filtergraph) → ffmpeg encode/concat with soft subtitles.

Uploading to GHL Memberships: use the `.mp4`; if GHL doesn't show embedded subtitles, upload the `.srt` or burn captions in.
