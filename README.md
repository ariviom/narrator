# narrator

Turn a book into a narrated audiobook in a **single cloned voice**, entirely on
your own machine. You give it (1) a short clean recording of the voice to clone
and (2) the book as plain-text chapters; it produces an MP3 per chapter plus one
combined `.m4b` with chapter markers. **No audio or text is ever uploaded.**

It clones one constant narration timbre and uses it for everything — it does not
do per-character voices (mixing dialogue voices into the reference makes the
clone sound averaged and inconsistent).

> Design rationale and a from-scratch build guide: [`docs/build-brief.md`](docs/build-brief.md).

## Requirements

- **Python 3.11** (a dedicated venv; avoids install friction on 3.12).
- An **NVIDIA GPU** is the happy path (~6 GB+ VRAM is comfortable). CPU works but
  is slow. Set `device: cpu` in `config/settings.yaml` if you have no GPU.
- **ffmpeg + ffprobe** on your PATH (clipping, silences, loudness, `.m4b`).
- A **~12–15 s clean, single-voice** audio clip to clone from. Short and clean
  beats long: calm narration-style prose, one speaker, no music or overlap.

## Install

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install chatterbox-tts          # the TTS backend (see "Notes" re: versions)
pip install -e .                    # exposes the `narrator` command
```

The first run downloads model weights once; after that it runs fully offline.

## Quickstart

1. **Prepare the voice reference** from your recording (any format ffmpeg reads).
   Clip ~15 s and convert to 24 kHz mono; the clip is auto-transcribed too:
   ```bash
   narrator prep-reference --source voice.wav --start 00:30 --end 00:45
   ```
   (If your source has chapter markers, `--candidates` prints a few clip windows
   to audition.) The result lands at `reference/ref.wav` (+ `ref.txt`).

2. **Add your book.** One folder per chapter under `stories/`, each containing a
   text file (configurable via `stories_dir`):
   ```
   stories/
     01_opening/01_opening.txt
     02_the-journey/02_the-journey.txt
   ```
   `--story` accepts a number (`1`), a folder name, or a title fragment.

3. **Voice-test one chunk**, then narrate a whole chapter, then the whole book:
   ```bash
   narrator normalize --story 1 --dry-run   # print exactly what the model will say
   narrator tts --story 1 --limit 1         # generate a single chunk to audition
   narrator narrate --story 1               # one chapter end to end -> out/01_opening.mp3
   narrator narrate --all                   # every chapter + combined out/audiobook.m4b
   ```

Generation is **cached and resumable** — a crash partway through doesn't
re-narrate what's already done. Work one chapter through end-to-end and tune the
reference clip + `config/pronunciation.yaml` before batching the whole book.

## Configuration

- **`config/settings.yaml`** — engine, device, fixed seed (keeps the voice
  consistent across chunks), chunk size, pause lengths, loudness targets
  (−18 LUFS / −3 dBTP), QA settings, and output paths.
- **`config/pronunciation.yaml`** — phonetic respellings and regex replacements
  for names/words the model mispronounces. Start from the examples and grow it by
  ear as you catch mistakes.

## How it works

1. **normalize** — drop any front-matter block, normalize quotes/dashes/ellipses,
   expand numbers (`23rd` → "twenty-third", `1880` → "eighteen eighty") and
   abbreviations (`Mr.`, `St.`, `No.` …), inline footnotes for reading, and apply
   the pronunciation dictionary.
2. **chunk** — pack sentences into ~250-char chunks (never splitting a sentence)
   to stay under model context and avoid long-form drift.
3. **generate** — synthesize each chunk with the fixed reference + fixed seed,
   cache by content hash, then **Whisper-re-transcribe and compare**; chunks that
   hallucinate/repeat/drop words are retried with a new seed (best take kept).
4. **stitch** — concatenate with paragraph-aware silences, two-pass loudness
   normalization, MP3 per chapter, and a combined `.m4b` with chapter markers.

## Swapping the TTS engine

The engine sits behind a tiny interface (`engines/base.py`:
`synthesize(text, reference, *, seed) -> AudioClip`). Normalization, chunking,
caching, QA, and stitching never import a specific backend, so changing engines
is a one-line `engine:` change in `settings.yaml` plus an adapter in `engines/`.
Chatterbox (MIT, clone-from-reference, no transcript required) is the default.

## Notes

- **Verify the Chatterbox API at install time** — it moves fast. Confirm the
  `from_pretrained` / `generate` signature against
  [pypi.org/project/chatterbox-tts](https://pypi.org/project/chatterbox-tts/) and
  [github.com/resemble-ai/chatterbox](https://github.com/resemble-ai/chatterbox);
  adapt `engines/chatterbox.py` if kwargs changed.
- **Consent:** only clone a voice you have permission to use.
- **Watermark:** Chatterbox applies an inaudible watermark to all output.
