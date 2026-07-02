import argparse, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def build_parser():
    p = argparse.ArgumentParser(prog="narrator")
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("prep-reference")
    pr.add_argument("--start"); pr.add_argument("--end")
    pr.add_argument("--source", help="audio file to clone the voice from (a recording or audiobook)")
    pr.add_argument("--candidates", action="store_true"); pr.add_argument("--chapter")
    nm = sub.add_parser("normalize"); nm.add_argument("--story", required=True); nm.add_argument("--dry-run", action="store_true")
    tt = sub.add_parser("tts"); tt.add_argument("--story", required=True)
    tt.add_argument("--limit", type=int); tt.add_argument("--chunk", type=int)
    st = sub.add_parser("stitch"); st.add_argument("--story", required=True)
    na = sub.add_parser("narrate"); na.add_argument("--story"); na.add_argument("--all", action="store_true")
    sub.add_parser("build-m4b")
    return p

def resolve_story(arg: str, stories_dir: Path) -> Path:
    dirs = sorted(d for d in stories_dir.iterdir() if d.is_dir())
    if arg.isdigit():
        prefix = f"{int(arg):02d}_"
        for d in dirs:
            if d.name == arg or d.name.startswith(prefix):
                return d
    else:
        for d in dirs:
            if d.name == arg:
                return d
    matches = [d for d in dirs if arg.lower() in d.name.lower()]
    if not matches:
        raise SystemExit(f"no story matching {arg!r}")
    return matches[0]

def _story_text(story_dir: Path) -> str:
    txt = next((p for p in story_dir.glob("*.txt") if p.name != "images.txt"), None)
    if txt is None:
        raise SystemExit(f"no story text file in {story_dir}")
    return txt.read_text()

def _stories_dir(settings) -> Path:
    d = settings.stories_dir
    return d if d.is_absolute() else (ROOT / d)

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    from .config import load_settings, load_pronunciation
    settings = load_settings(ROOT / "config/settings.yaml")
    pron = load_pronunciation(ROOT / "config/pronunciation.yaml")
    stories = _stories_dir(settings)

    if args.cmd == "prep-reference":
        from .reference import candidate_windows, prepare_reference
        from .transcribe import WhisperTranscriber
        if not args.source:
            raise SystemExit("prep-reference requires --source PATH (the audio to clone the voice from)")
        if args.candidates:
            for w in candidate_windows(args.source, args.chapter): print(w)
            return 0
        prepare_reference(args.source, args.start, args.end, settings.ref_wav,
                          settings.ref_transcript,
                          WhisperTranscriber(settings.whisper_model, device=settings.device))
        print("wrote", settings.ref_wav); return 0

    if args.cmd == "normalize":
        from .normalize import normalize_story
        from .chunk import chunk_paragraphs
        ns = normalize_story(_story_text(resolve_story(args.story, stories)), pron,
                             speak_subtitle=settings.speak_subtitle)
        chunks = chunk_paragraphs(ns.paragraphs, settings.max_chars)
        if args.dry_run:
            print(f"# {ns.title}  ({len(chunks)} chunks)")
            for c in chunks: print(f"[{c.index:03d}|p{c.paragraph_index}] {c.text}")
        return 0

    if args.cmd in ("tts", "stitch", "narrate", "build-m4b"):
        from .normalize import normalize_story
        from .chunk import chunk_paragraphs
        from .engines import load_engine
        from .engines.base import Reference
        from .generate import generate_story
        from .stitch import assemble_story, export_mp3, build_m4b
        from .transcribe import WhisperTranscriber

        def narrate_one(story_dir: Path):
            ns = normalize_story(_story_text(story_dir), pron, speak_subtitle=settings.speak_subtitle)
            if settings.speak_title and ns.title:
                ns.paragraphs.insert(0, ns.title + ".")
            chunks = chunk_paragraphs(ns.paragraphs, settings.max_chars)
            if args.cmd == "tts" and getattr(args, "limit", None):
                chunks = chunks[: args.limit]
            engine = load_engine(settings)
            ref = Reference(settings.ref_wav, settings.ref_transcript.read_text() if settings.ref_transcript.exists() else None)
            tr = WhisperTranscriber(settings.whisper_model, device=settings.device) if settings.qa_enabled else None
            cache = ROOT / "cache" / story_dir.name
            paths = generate_story(chunks, engine, ref, settings, cache, tr)
            if args.cmd in ("stitch", "narrate"):
                samples, sr = assemble_story(paths, chunks, settings)
                export_mp3(samples, sr, settings.mp3_dir / f"{story_dir.name}.mp3", settings, title=ns.title)
            return ns.title

        if args.cmd == "build-m4b" or (args.cmd == "narrate" and getattr(args, "all", False)):
            from .audio import read_wav  # noqa
            stories_list = sorted(d for d in stories.iterdir() if d.is_dir())
            titles = [narrate_one(d) for d in stories_list] if args.cmd == "narrate" else \
                     [d.name for d in stories_list]
            wavs = [settings.mp3_dir / f"{d.name}.mp3" for d in stories_list]  # re-decoded by ffmpeg
            build_m4b(wavs, titles, settings.m4b_path)
            print("wrote", settings.m4b_path); return 0

        if not getattr(args, "all", False) and not args.story:
            raise SystemExit("narrator narrate requires --story STORY or --all")
        narrate_one(resolve_story(args.story, stories)); return 0
    return 1

if __name__ == "__main__":
    sys.exit(main())
