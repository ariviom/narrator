import json, subprocess
from pathlib import Path
from .engines.base import Reference

def build_clip_cmd(src: Path, start: str, end: str, out: Path) -> list:
    return ["ffmpeg", "-y", "-ss", start, "-to", end, "-i", str(src),
            "-ac", "1", "-ar", "24000", "-vn", str(out)]

def prepare_reference(src, start, end, out_wav, out_txt, transcriber) -> Reference:
    out_wav = Path(out_wav); out_wav.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(build_clip_cmd(Path(src), start, end, out_wav), check=True)
    text = transcriber.transcribe(out_wav)
    Path(out_txt).write_text(text)
    return Reference(out_wav, text)

def _chapters(src: Path) -> list:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_chapters", "-of", "json", str(src)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out).get("chapters", [])

def _hhmmss(seconds: float) -> str:
    s = int(seconds); return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"

def candidate_windows(src, chapter=None, n=3, clip_len=14) -> list:
    chaps = _chapters(Path(src))
    if chapter:
        chaps = [c for c in chaps if chapter.lower() in c.get("tags", {}).get("title", "").lower()]
    windows = []
    for c in chaps[:n]:
        start = float(c["start_time"]) + 30.0   # skip into the chapter, past any date read-aloud
        windows.append((_hhmmss(start), _hhmmss(start + clip_len)))
    return windows
