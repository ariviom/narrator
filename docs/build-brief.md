---
title: "Voice-Cloned Narration — Build Brief"
type: spec
status: Reference
date: 2026-07-01
eyebrow: Design rationale & from-scratch guide
dek: How this local pipeline narrates a book in a single cloned voice.
pills:
  - { label: Engine, value: "Chatterbox (local, MIT)" }
  - { label: Runs, value: "Offline on an NVIDIA GPU" }
  - { label: Output, value: "MP3s + combined .m4b" }
---

# Voice-Cloned Narration — Build Brief

*This distills how the pipeline works and why it's built this way. It pairs with the [README](../README.md), which has install steps and the exact commands. Read it alongside the code here, or paste the whole file into Claude Code as a starting brief to adapt or rebuild it for your own book and voice.*

---

## What it does

You give it (1) **one short clean recording** of the voice you want to clone and (2) the **book text** as plain files. It clones that single voice and reads the whole book in it, producing an MP3 per chapter plus one combined `.m4b` audiobook with chapter markers. **Everything runs locally — no audio or text is ever uploaded.**

It clones *one constant narration timbre* and uses it for everything. It does **not** do per-character voices — that's a deliberate non-goal (mixing dialogue voices into the reference makes the clone sound averaged and inconsistent).

---

## What you need before starting

**Inputs**
- **A voice reference: ~12–15 seconds of clean, single-voice speech** from your source recording. This is the single biggest quality lever. Pick a passage that is:
  - calm, plain narration-style prose (not laughing, not shouting, not doing character voices),
  - one person only (no overlapping voices, no music, no background noise),
  - consistent in tone.
  - **Short beats long.** Counterintuitively, ~15 s of clean audio clones better than several minutes. Convert it to **24 kHz mono WAV**.
- **The book as plain text** — one `.txt` (or `.md`) file per chapter, in a folder. Chapter = one output track.

**Hardware**
- An **NVIDIA GPU** is the happy path (the reference build used an RTX 3090 / 24 GB, but Chatterbox inference is comfortable on ~6 GB+). 
- No NVIDIA GPU? Options: rent a cloud GPU box for a few hours (cheapest reliable path), or run on CPU (works, just slow). Avoid cloud TTS APIs if privacy matters — they upload the voice and the text.
- **ffmpeg + ffprobe** installed (for clipping, silences, loudness, and building the `.m4b`).

**Consent & watermark note**
- If you're cloning someone else's voice, get their explicit OK first. (Cloning a voice you don't have rights to isn't okay.)
- Chatterbox stamps an **inaudible watermark** on all output. Fine for personal use; just know it's there.

---

## Key design decisions (and why)

| Decision | Choice | Why |
|---|---|---|
| Local vs cloud | **Local / offline** | Nothing is uploaded; a modest GPU handles it fine. |
| TTS engine | **Chatterbox** (Resemble AI) | MIT-licensed (commercial-safe), simplest clone API (no reference transcript needed), expressive English, tuned for long-form narration. |
| Fallback engine | **Qwen3-TTS** (Apache-2.0) | Documented swap-in behind the same interface if Chatterbox disappoints. |
| Python | **3.11 venv** | Avoids Chatterbox's known install friction on 3.12. |
| Reference clip | **~12–15 s, mono, single-voice** | Short clean references beat long ones for every engine. |
| Chunking | **Sentence-grouped, ~250 chars** | Stays under model context; prevents long-form drift. Never split mid-sentence. |
| Quality control | **Whisper re-transcribe + retry** | Auto-catches hallucination / repeats / dropped words; retries the bad chunk with a new seed. |
| Voice consistency | **One fixed reference + fixed random seed** | Keeps timbre stable across thousands of chunks. |
| Output | **MP3 per chapter + one combined `.m4b`** | Portable singles plus a navigable whole-book audiobook. |
| Loudness | **−18 LUFS, −3 dBTP** (ffmpeg `loudnorm`) | Audiobook-standard, consistent across devices. |

**The one architectural rule that matters:** the TTS engine sits behind a tiny interface (`synthesize(text, reference, seed) -> audio`). Normalization, chunking, caching, QA, and stitching never import a specific engine. So swapping Chatterbox → Qwen (or a future model) is a one-line config change.

---

## The pipeline (build it in this order)

**A. Reference prep**
- Take the chosen slice of your source recording and convert to 24 kHz mono WAV:
  `ffmpeg -ss <start> -to <end> -i input.wav -ac 1 -ar 24000 -vn reference/ref.wav`
- Auto-transcribe it once with local **Whisper** → `reference/ref.txt` (free; the Qwen fallback and the QA step reuse it).

**B. Text normalization** (turns raw prose into exactly what the model should say)
1. Strip any markup/HTML; normalize smart quotes, em/en dashes, ellipses, whitespace.
2. Expand numbers with `num2words`: cardinals, ordinals (`23rd` → "twenty-third"), years (`1880` → "eighteen eighty").
3. Expand abbreviations (`Mr.` → "Mister", `St.` → "Saint" or "Street" — pick per book, etc.).
4. Apply a **pronunciation dictionary** (`pronunciation.yaml`) — phonetic respellings for names/invented words the model mangles (e.g. `Siobhan: "Shiv-awn"`). You grow this by ear.
5. A `--dry-run` prints exactly what the model will receive, without touching the GPU. Use it constantly.

**C. Chunking**
- Split into sentences, then greedily pack them into ~250-char chunks. Never split a sentence; a single over-long sentence splits on clause punctuation. Track paragraph boundaries (for longer pauses later).

**D. Generation loop** (the part that takes real time)
- For each chunk: `hash = sha1(normalized_text + reference + engine + params + seed)`.
- If `cache/<chapter>/<hash>.wav` exists, reuse it. **This makes runs idempotent and resumable** — a crash three hours in doesn't re-narrate what's done.
- Else synthesize with the fixed reference + fixed seed, write to cache.
- **QA:** Whisper-transcribe the generated clip, fuzzy-compare to the expected text. If word-error/length drift is too high (hallucination/repeat/skip), retry with a new seed, up to N times, keeping the closest match. Log chunks that still fail for manual review.
- `--limit 1` / `--chunk i` generate a single chunk for a fast **voice test** before committing to a whole chapter.

**E. Stitch & export**
- Concatenate cached chunks in order; insert ~350 ms of silence within a paragraph, ~600 ms between paragraphs.
- Loudness-normalize (ffmpeg `loudnorm`, two-pass) to −18 LUFS / −3 dBTP.
- Export one MP3 per chapter with title/track metadata.
- Build the combined `.m4b`: concatenate all chapters, write **chapter markers** (one per chapter, named + ordered), encode AAC.

---

## Config files

**`settings.yaml`** — engine choice, device (`cuda`), fixed seed, engine knobs (`cfg ≈ 0.3` for deliberate pacing, `exaggeration ≈ 0.5`), chunk size, pause lengths, loudness targets, QA on/off + Whisper model + retry count, and where chapters live + output paths.

**`pronunciation.yaml`** — a growing list of respellings and regex replacements for names/words the model gets wrong. Start from the examples and grow it by ear as you catch mispronunciations in milestone 1.

---

## CLI shape

```
prep-reference --source recording.wav --start MM:SS --end MM:SS
normalize --story 1 --dry-run        # print what the model will say
tts --story 1 --limit 1              # single-chunk voice test
tts --story 1                        # full chapter (cached / resumable)
stitch --story 1                     # silences + loudnorm + MP3
narrate --story 1                    # normalize -> tts -> stitch end to end
narrate --all                        # every chapter + build combined .m4b
```

---

## How to actually work through it (do NOT batch first)

Work one chapter at a time before committing compute to the whole book:

1. **Milestone 1 — one chapter, end to end.** Prep the reference → single-chunk voice test → tune the reference clip and `pronunciation.yaml` on one *short* chapter until it sounds right → narrate the full chapter → **listen**.
2. **Milestone 2 — harden.** Confirm caching/resume, QA-retry behavior, and loudness on that chapter.
3. **Milestone 3 — batch.** `narrate --all`, build the combined `.m4b`, spot-check.

The reference clip and pronunciation dictionary are where nearly all the tuning happens. Budget your attention there.

---

## Dependencies (verify current versions at build time — these libraries drift fast)

- Python **3.11** venv.
- **PyTorch CUDA build** matched to your GPU.
- `chatterbox-tts` (primary). Check [pypi.org/project/chatterbox-tts](https://pypi.org/project/chatterbox-tts/) and [github.com/resemble-ai/chatterbox](https://github.com/resemble-ai/chatterbox) for the current `from_pretrained` / `generate` signature before pinning — the API moves.
- `faster-whisper` (reference transcript + QA), `num2words`, `pyyaml`, `soundfile`, `numpy`.
- `ffmpeg` / `ffprobe`.

First run downloads model weights once; after that it's fully offline.

---

## Optional next step — a web player

A natural companion is a small web app to listen in the browser: play/pause, ±15 s, scrubber, speed, chapter list, resume-where-you-left-off, and lock-screen controls (via the Media Session API). The reference build did this with a static Astro site plus one persistent React audio "island," password-gated behind an edge function so both pages and the audio files stay private. Entirely separate from the narration engine here — build it only once the audio is good.
