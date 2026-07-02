import json, subprocess, tempfile
from pathlib import Path
import numpy as np
from .audio import read_wav, write_wav, silence

def assemble_story(clip_paths, chunks, settings):
    sr = None; parts = []
    for i, (path, ch) in enumerate(zip(clip_paths, chunks)):
        data, csr = read_wav(path); sr = sr or csr
        if i > 0:
            ms = settings.pause_inter_ms if ch.is_paragraph_start else settings.pause_intra_ms
            parts.append(silence(ms, sr))
        parts.append(data)
    return (np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)), (sr or 24000)

def _ln(settings):
    return f"loudnorm=I={settings.loud_i}:TP={settings.loud_tp}:LRA={settings.loud_lra}"

def loudnorm_pass1_cmd(in_wav, settings):
    return ["ffmpeg", "-y", "-i", str(in_wav), "-af",
            _ln(settings) + ":print_format=json", "-f", "null", "-"]

def loudnorm_pass2_cmd(in_wav, out, settings, measured):
    flt = (_ln(settings) +
           f":measured_I={measured['input_i']}:measured_TP={measured['input_tp']}"
           f":measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}"
           f":offset={measured['target_offset']}:linear=true")
    return ["ffmpeg", "-y", "-i", str(in_wav), "-af", flt, "-ar", "24000", str(out)]

def _measure(in_wav, settings) -> dict:
    res = subprocess.run(loudnorm_pass1_cmd(in_wav, settings), capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg loudnorm pass-1 failed:\n{res.stderr}")
    stderr = res.stderr
    blob = stderr[stderr.rindex("{"): stderr.rindex("}") + 1]
    return json.loads(blob)

def export_mp3(samples, sr, out_mp3, settings, *, title=None):
    out_mp3 = Path(out_mp3); out_mp3.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw.wav"; norm = Path(td) / "norm.wav"
        write_wav(raw, samples, sr)
        m = _measure(raw, settings)
        subprocess.run(loudnorm_pass2_cmd(raw, norm, settings, m), check=True,
                       capture_output=True)
        meta = ["-metadata", f"title={title}"] if title else []
        subprocess.run(["ffmpeg", "-y", "-i", str(norm), *meta,
                        "-codec:a", "libmp3lame", "-q:a", "2", str(out_mp3)],
                       check=True, capture_output=True)

def _ffmeta_escape(s: str) -> str:
    # FFMETADATA requires escaping of '=', ';', '#', '\' and newlines.
    for ch in ("\\", "=", ";", "#"):
        s = s.replace(ch, "\\" + ch)
    return s.replace("\n", " ")

def _ffmeta_chapters(durations_s, titles) -> str:
    lines = [";FFMETADATA1"]; t = 0.0
    for dur, title in zip(durations_s, titles):
        start_ms = int(round(t * 1000)); end_ms = int(round((t + dur) * 1000)); t += dur
        lines += ["[CHAPTER]", "TIMEBASE=1/1000",
                  f"START={start_ms}", f"END={end_ms}",
                  f"title={_ffmeta_escape(title)}"]
    return "\n".join(lines) + "\n"

def _probe_duration(path) -> float:
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}:\n{res.stderr}")
    return float(res.stdout.strip())

def build_m4b(story_wavs, titles, out_m4b):
    """Build a chaptered M4B from a list of audio inputs (MP3 or WAV).

    Uses ffmpeg's concat demuxer to join the inputs and an FFMETADATA file for
    one chapter per input, so inputs are never decoded by soundfile (which
    cannot read MP3)."""
    out_m4b = Path(out_m4b); out_m4b.parent.mkdir(parents=True, exist_ok=True)
    durs = [_probe_duration(w) for w in story_wavs]
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        listing = td / "inputs.txt"
        listing.write_text("".join(
            f"file '{Path(w).resolve()}'\n" for w in story_wavs))
        meta = td / "meta.txt"; meta.write_text(_ffmeta_chapters(durs, titles))
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
             "-i", str(meta), "-map_metadata", "1",
             "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
             str(out_m4b)],
            check=True, capture_output=True)
